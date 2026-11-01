"""Deterministic, deliberately narrow OpenAPI 3.1 client generation.

Unsupported schema/operation features stop generation; they never become Any.
Run through the frozen API environment. --check reads without modifying files.
"""
import argparse
import hashlib
import json
import keyword
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = 1
PREFIX = "#/components/schemas/"
KEYWORDS = {
    "title", "description", "type", "properties", "required", "additionalProperties",
    "$ref", "enum", "const", "minLength", "maxLength", "pattern",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identifier(value):
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", value)
            and not keyword.iskeyword(value)
            and value not in ("constructor", "prototype", "__proto__"), "Unsupported identifier")
    return value


def schema_check(schema, schemas, active=()):
    require(isinstance(schema, dict) and set(schema) <= KEYWORDS, "Unsupported schema keyword")
    if "$ref" in schema:
        ref = schema["$ref"]
        require(isinstance(ref, str) and ref.startswith(PREFIX), "Only local schema references supported")
        name = ref[len(PREFIX):]
        require(name in schemas and name not in active, "Missing or recursive schema reference")
        require(set(schema) <= {"$ref", "title", "description"}, "Reference siblings unsupported")
        schema_check(schemas[name], schemas, (*active, name))
        return
    kind = schema.get("type")
    require(kind in ("object", "string", "boolean"), "Unsupported schema type")
    if kind == "object":
        require(schema.get("additionalProperties") is False, "Objects must reject unknown properties")
        properties, required = schema.get("properties"), schema.get("required")
        require(isinstance(properties, dict) and isinstance(required, list)
                and set(required) == set(properties) and len(required) == len(properties),
                "Only fully required object fields are currently supported")
        for name, child in properties.items():
            identifier(name)
            schema_check(child, schemas, active)
        require(not (set(schema) & {"enum", "const", "pattern", "minLength", "maxLength"}),
                "Object scalar constraints unsupported")
    else:
        require(not (set(schema) & {"properties", "required", "additionalProperties"}),
                "Scalar object constraints unsupported")
        expected = str if kind == "string" else bool
        for key in ("const",):
            if key in schema:
                require(type(schema[key]) is expected, "Literal type mismatch")
        if "enum" in schema:
            require(isinstance(schema["enum"], list) and schema["enum"]
                    and all(type(item) is expected for item in schema["enum"]), "Enum type mismatch")
        if kind == "boolean":
            require(not (set(schema) & {"pattern", "minLength", "maxLength"}),
                    "Boolean string constraints unsupported")
        for key in ("minLength", "maxLength"):
            if key in schema:
                require(type(schema[key]) is int and 0 <= schema[key] <= 65536, "Invalid string bound")
        if "pattern" in schema:
            # Portable subset used by this contract, without dialect-specific
            # lookarounds/backreferences or executable generator expressions.
            require(schema["pattern"] == "^[a-z][a-z0-9_-]*$", "Unsupported regular expression")


def model_type(schema, language):
    if "$ref" in schema:
        return identifier(schema["$ref"][len(PREFIX):])
    values = [schema["const"]] if "const" in schema else schema.get("enum")
    if values is not None:
        if language == "ts":
            return " | ".join(json.dumps(value) for value in values)
        return "Literal[" + ", ".join(repr(value) for value in values) + "]"
    return {"ts": {"string": "string", "boolean": "boolean"},
            "py": {"string": "str", "boolean": "bool"}}[language][schema["type"]]


def generate_files(document):
    require(document.get("openapi") == "3.1.0" and document.get("x-contract-version") == "1.0",
            "Unsupported API contract version")
    require(not document.get("security") and not document.get("servers"),
            "Authentication and remote server generation require a reviewed extension")
    schemas = document["components"]["schemas"]
    require(isinstance(schemas, dict) and schemas, "No canonical schemas")
    for name, schema in schemas.items():
        identifier(name)
        schema_check(schema, schemas, (name,))
    operations = {}
    for path, item in sorted(document["paths"].items()):
        require(re.fullmatch(r"/api/[a-z][a-z0-9/-]*", path) and "//" not in path,
                "Unsupported operation path")
        require(set(item) == {"get"}, "Only explicitly reviewed read-only operations supported")
        operation = item["get"]
        require(not operation.get("parameters") and not operation.get("requestBody")
                and not operation.get("security"), "Request inputs/auth require generator extension")
        name = identifier(operation["operationId"])
        require(name not in operations, "Duplicate operation identifier")
        responses = operation["responses"]
        require(set(responses) == {"200", "400", "404", "405", "500"},
                "Every documented success/error status must be generated")
        types = {}
        for status, response in responses.items():
            require(set(response["content"]) == {"application/json"}, "Only JSON responses supported")
            ref = response["content"]["application/json"]["schema"]
            require(set(ref) == {"$ref"}, "Response must reference a canonical model")
            schema_check(ref, schemas)
            types[status] = ref["$ref"][len(PREFIX):]
        errors = {}
        for status in ("400", "404", "405", "500"):
            code = responses[status].get("x-error-code")
            require(code in schemas["ErrorDetail"]["properties"]["code"]["enum"],
                    "Error status needs its canonical error code")
            errors[status] = {"schema": types[status], "code": code}
        operations[name] = {"path": path, "response": types["200"], "errors": errors}
    require(operations, "No operations")
    canonical = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    results = {"contracts/openapi.json": canonical}
    for language, target in (("ts", "apps/web/src/generated/api.ts"),
                             ("py", "services/api/umami_api/generated_client.py")):
        types, methods = [], []
        for name, schema in sorted(schemas.items()):
            if schema["type"] != "object":
                assignment = "export type " + name + " = " if language == "ts" else name + " = "
                types.append(assignment + model_type(schema, language) + (";" if language == "ts" else ""))
                continue
            if language == "ts":
                fields = ["  readonly " + key + ": " + model_type(child, language) + ";"
                          for key, child in sorted(schema["properties"].items())]
                types.append("export interface " + name + " {\n" + "\n".join(fields) + "\n}")
            else:
                fields = ["    " + key + ": " + model_type(child, language)
                          for key, child in sorted(schema["properties"].items())]
                types.append("class " + name + "(TypedDict):\n" + "\n".join(fields))
        for name, operation in operations.items():
            result = operation["response"]
            if language == "ts":
                camel = re.sub(r"_([a-z])", lambda match: match[1].upper(), name)
                methods.append("  async " + camel + "(signal?: AbortSignal): Promise<" + result + "> {\n"
                               "    return await this.request(" + json.dumps(name) + ", signal) as " + result + ";\n  }")
            else:
                methods.append("    def " + name + "(self) -> " + result + ":\n"
                               "        return cast(" + result + ", self._request(" + repr(name) + "))")
        template = (ROOT / ("scripts/templates/api_client." + language + ".in")).read_text()
        replacements = {"__DIGEST__": digest, "__TYPES__": "\n\n".join(types),
                        "__METHODS__": "\n\n".join(methods)}
        for token, value in (("__SCHEMAS__", schemas), ("__OPERATIONS__", operations)):
            serialized = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
            replacements[token] = serialized if language == "ts" else repr(serialized)
        for token, value in replacements.items():
            require(token in template, "Generator template marker missing")
            template = template.replace(token, value)
        results[target] = template
    manifest = {"contractVersion": document["x-contract-version"], "generatorVersion": VERSION,
                "sha256": {path: hashlib.sha256(value.encode()).hexdigest()
                           for path, value in sorted(results.items())}}
    results["contracts/manifest.json"] = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    return results


def check_or_write(root, outputs, *, check):
    mismatches = []
    for path, content in outputs.items():
        target = root / path
        if check:
            if not target.is_file() or target.read_bytes() != content.encode():
                mismatches.append(path)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content.encode())
    return mismatches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    sys.path.insert(0, str(ROOT / "services/api"))
    from umami_api.main import app
    outputs = generate_files(app.openapi())
    mismatches = check_or_write(ROOT, outputs, check=arguments.check)
    if mismatches:
        print("API contract drift: " + ", ".join(mismatches), file=sys.stderr)
        return 1
    print("Canonical API and both generated clients are current." if arguments.check else
          "Generated canonical API and both clients; review and commit all four artifacts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
