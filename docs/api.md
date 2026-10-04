
# Documentation

Namespaces: [main](#main)

---

# main

## Errors for 'main'

```js
// Thrown when text is not YAML, or does not fit what it is read into.
+ error Error (syntax, duplicate, type, limit) payload { message: String, line: uint (0), column: uint (0) }
```

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
