package edu.uic.cs441.scholarchain.services

/** Nesting bound for JSON request bodies, checked on the raw text before any parse.
  *
  * ujson parses iteratively, but building, rendering or transforming a parsed value recurses once
  * per nesting level, and an error message for a wrong-shaped value renders the whole value. A body
  * of a few thousand `[` therefore overflowed the stack in that recursion (a `StackOverflowError`,
  * which `NonFatal` does not catch) and the transport answered an untyped 500. Every request-body
  * parser in this module (`QueryRequest.parse`, `PublicSemanticRoute.validate`,
  * `SemanticApi.retrieve`) calls [[withinDepth]] first and answers a typed 400 `INVALID_REQUEST`
  * when it fails, so a deep body never reaches ujson.
  *
  * The scan is a single loop over the characters with constant state: no recursion, no allocation,
  * no dependence on the thread stack size or on JIT compilation.
  */
object RequestJson {

  /** Maximum number of arrays and objects open at once in a request body. The deepest legitimate
    * body is 3 (`/v1/query` root object, `constraints`, `topics` array); `/v1/semantic/retrieve`
    * and the internal semantic route are at most 2 (root object, `filters`).
    */
  val MaxNestingDepth = 32

  /** True when `text` never has more than `maxDepth` arrays/objects open at once and never closes
    * more than it opened. `[` `{` `]` `}` inside JSON strings are ignored; a backslash escapes the
    * next character inside a string. Other malformations are left to the parser, which rejects
    * them; this scan only bounds depth.
    */
  def withinDepth(text: String, maxDepth: Int = MaxNestingDepth): Boolean = {
    var depth = 0
    var inString = false
    var escaped = false
    var ok = true
    var i = 0
    while (ok && i < text.length) {
      val c = text.charAt(i)
      if (inString) {
        if (escaped) escaped = false
        else if (c == '\\') escaped = true
        else if (c == '"') inString = false
      } else if (c == '"') inString = true
      else if (c == '[' || c == '{') { depth += 1; ok = depth <= maxDepth }
      else if (c == ']' || c == '}') { depth -= 1; ok = depth >= 0 }
      i += 1
    }
    ok
  }
}
