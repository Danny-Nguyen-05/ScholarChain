package edu.uic.cs441.scholarchain.core

enum ViolationCode {
  case MissingValidationContext
  case MissingProvenance
  case InvalidConfidence
  case UnsupportedSchemaVersion
  case MalformedId
  case InvalidPairOrder
  case ReversedTimeWindow
  case UnconfirmedIdentity
  case InconsistentRecord
  case MalformedInput
}

final case class DomainViolation(code: ViolationCode, message: String)
