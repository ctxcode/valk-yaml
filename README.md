# valk-yaml

YAML for [Valk](https://valk-lang.dev): reading and writing YAML 1.2, straight into and out of
your own classes. Purely written in Valk, with no os-package dependencies.

Requires Valk 0.8.1 or newer.

## Install

```
vman install github.com/ctxcode/valk-yaml
```

## Example

```rust
use yaml
use valk.fs

class Server {
    host: String ("127.0.0.1")
    port: uint (8080)
}

class Settings {
    name: String
    debug: bool (false)
    tags: Array[String] (.{})
    server: Server
}

fn main() {
    let text = fs.read("config.yaml") ! panic("Cannot read config.yaml")
    let settings = yaml.decode_to[Settings](text) ! panic(E.message)
    println(settings.server.port)

    fs.write("config.yaml", yaml.encode_of(settings)) ! panic("Cannot write config.yaml")
}
```

Every field of the class must be in the document, unless it is nullable or has a default. The
error names the key: `'server.host' is missing`, `'server.port' should be an integer that fits
the field`. A `time.DateTime` field takes a YAML timestamp (`2001-12-14t21:59:43.10-05:00`,
`2002-12-14`), converted to UTC.

## When the shape is not fixed

`decode` returns a `json.Value`, the document type of the standard library's `json` package, so
everything that works with JSON works here:

```rust
let document = yaml.decode(text) ! panic("%{E.message}")
println(document["server"]["port"].int)
println(document["tags"][0].string)
each document["servers"].array as server : println(server["name"].string)
```

`yaml.encode(document)` writes one back out. A text with several documents, separated by `---`,
is read with `decode_all` and written with `encode_all`.

## What it reads

- Block mappings and sequences, including the compact forms (`- a: 1`, `- - x`) and a
  sequence at the indent of its key.
- Flow collections (`[a, b]`, `{a: 1}`) over as many lines as they like, and JSON.
- Plain, single-quoted and double-quoted scalars with every escape, over several lines.
- Literal (`|`) and folded (`>`) block scalars with chomping (`-`, `+`) and indentation
  indicators.
- Comments, anchors (`&a`) and aliases (`*a`), merge keys (`<<: *base`, `<<: [*a, *b]`),
  explicit keys (`? key`), several documents (`---`, `...`), `%YAML` and `%TAG` directives.

Scalars follow YAML 1.2's core schema: `null`, `~` and an empty value are null; `true` and
`false` (and `True`, `TRUE`, ...) are bools; `12`, `0o17` and `0x1F` are integers; `1.5`, `1e3`,
`.inf` and `.nan` are floats; everything else, and everything quoted, is a string. So `yes`, `on`
and `0755` are the text and the integer they look like in YAML 1.2, not YAML 1.1's bool and octal
number. The tags `!!str`, `!!int`, `!!float`, `!!bool` and `!!null` override that; a tag this
package does not know keeps a scalar's text.

Mapping keys are strings, as written: `1: one` has the key `"1"`. A mapping that gives a key twice
is an error, and merged keys come before a mapping's own, which win.

An alias shares the value its anchor holds. Aliases may expand a document to a million values,
and beyond that to ten times the values written out, after which reading stops with `limit`; so
does nesting deeper than 256 levels.

Not supported: mappings and sequences as keys (`[a, b]: c`, `? [a]`), as a `json.Value` only has
text keys, and an alias to a node from inside that node.

## Writing

`encode` and `encode_of` write block style, two spaces deep, with sequences indented under their
key. A string is quoted only when it has to be: when it would read back as something else
(`"true"`, `"12"`, `"null"`), holds characters that mean something in YAML, or would read as a
bool, number or date to a YAML 1.1 reader such as PyYAML (`"yes"`, `"0755"`, `"2001-12-14"`).
A string of several lines is written as a literal block. Floats always keep a `.` or an exponent,
so they read back as floats.

## Errors

`syntax`, `duplicate` (a key given twice), `type` (a tag or a class field that does not fit) and
`limit` (an alias bomb, or nesting too deep), each with the `line` and `column` where the reader
stopped:

```rust
yaml.decode(text) ! {
    println(E.message + " at line " + E.line + ", column " + E.column)
    return
}
// A flow sequence was not closed at line 1, column 7
```

## Benchmarks

Reading and writing a 22 MB file of 100,000 records (nested mappings, sequences, strings,
numbers), built with `--release`, on an AMD Ryzen 5 7600X; best of several runs:

| | Read | Write |
|---|---|---|
| valk-yaml | 0.28 s | 0.07 s |
| PyYAML 6.0.3 with libyaml (`CSafeLoader`, `CSafeDumper`) | 9.6 s | 6.5 s |

## Development

`make test` runs the suite, `make example` runs the example, `make lint` checks the sources and
`make docs` regenerates the API documentation. `python3 tests/crosscheck.py` (with `pyyaml` and
`ruamel.yaml` installed) regenerates `tests/python-samples.valk`, documents read by PyYAML and
ruamel.yaml that the suite reads and writes back.
