
# Documentation

Namespaces: [main](#main)

---

# main

## Errors for 'main'

```js
// Thrown when text is not YAML, or does not fit what it is read into.
+ error Error (syntax, duplicate, type, limit) payload { message: String, line: uint (0), column: uint (0) }
```

### Error

Thrown when text is not YAML, or does not fit what it is read into.

- `syntax`: the text does not read as YAML.
- `duplicate`: a mapping has the same key twice.
- `type`: a value is not what its tag or the type it is read into needs.
- `limit`: aliases expand to too many values, or values nest too deep.

`line` and `column` say where the reader stopped, counting from one, so the message can be
shown against the file. They are 0 for `type` errors from `decode_to`, whose message names the
key instead.

## Functions for 'main'

```js
// Reads one YAML document and returns it as a `json.Value`, so everything that works with JSON works with it.
+ fn decode(text: String) Value !Error
// Reads every document in a YAML text, the ones that `---` starts.
+ fn decode_all(text: String) Array[Value] !Error
// Reads one YAML document into a class or struct of your own.
+ fn decode_to[T](text: String) T !Error
// Writes a `json.Value` as a YAML document in block style.
+ fn encode(value: Value) String
// Writes several YAML documents, with `---` between them.
+ fn encode_all(documents: Array[Value]) String
// Writes a class or struct of your own as YAML, the way `json.from` would read it; a `time.DateTime` field is written as a date and time in UTC.
+ fn encode_of(value: $T) String
```

### decode

Reads one YAML document and returns it as a `json.Value`, so everything that works with JSON
works with it.

Scalars follow YAML 1.2's core schema: `null`, `~` and nothing are null, `true`/`false` are
bools, `12`, `0x1f` and `0o17` are integers, `1.5`, `1e3`, `.inf` and `.nan` are floats, and
anything else, or anything quoted, is a string. Mapping keys are strings, as written. An
empty text is null; a text with more than one document throws, see `decode_all`.

```valk
let config = yaml.decode(fs.read("config.yaml") !!) ! panic("%{E.message}")
println(config["server"]["port"].int)
```

### decode_all

Reads every document in a YAML text, the ones that `---` starts.

```valk
each yaml.decode_all(text) ! panic("%{E.message}") as document {
    println(document["kind"].string)
}
```

### decode_to

Reads one YAML document into a class or struct of your own.

Every field must be in the document, unless it is nullable or has a default. A value that
does not fit throws `.type`, and its message names the key, such as `'server.port' is
missing`. A `time.DateTime` field takes a date, or a date and time, converted to UTC.

```valk
class Settings {
    name: String
    port: uint (8080)
}

let settings = yaml.decode_to[Settings](text) ! panic("%{E.message}")
```

### encode

Writes a `json.Value` as a YAML document in block style.

A string is quoted only when it has to be: when it would read back as something else, such
as `"true"`, `"1.0"` or `"null"`, or holds characters that mean something in YAML. A string of
several lines is written as a literal block (`|`). An empty mapping or sequence is written as
`{}` or `[]`.

```valk
fs.write("config.yaml", yaml.encode(document)) ! panic("%{E.message}")
```

### encode_all

Writes several YAML documents, with `---` between them.

### encode_of

Writes a class or struct of your own as YAML, the way `json.from` would read it; a
`time.DateTime` field is written as a date and time in UTC.
