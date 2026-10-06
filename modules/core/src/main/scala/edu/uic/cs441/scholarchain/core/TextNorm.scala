package edu.uic.cs441.scholarchain.core

import java.util.Locale

/** Deterministic text normalization. It does not decide that two strings are one person. */
object TextNorm {
  def personName(raw: String): String = collapse(raw)

  /** Lowercase, collapse whitespace, and drop one trailing ASCII period. */
  def title(raw: String): String = {
    val collapsed = collapse(raw)
    if (collapsed.endsWith(".") && !collapsed.endsWith("...")) collapsed.dropRight(1)
    else collapsed
  }

  def collapse(raw: String): String =
    raw.trim.toLowerCase(Locale.ROOT).replaceAll("\\s+", " ")
}
