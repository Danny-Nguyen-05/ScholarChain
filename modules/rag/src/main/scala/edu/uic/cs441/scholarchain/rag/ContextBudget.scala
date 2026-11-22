package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*

/** Model-context byte budget in force for one plan.
  *
  * `retrieval.contextTokenBudget` sizes a single-entity answer (one metric, one component, one
  * ranking prefix). Direct-coauthor and shortest-path answers are atomic lists of per-collaboration
  * rows whose size grows with the bounded graph page (`retrieval.graphLimit`), so a researcher with
  * 22 coauthors needs several times that budget and Session 1 abstained on all 24 such questions
  * with `essential-evidence-context-budget`. For those two operations the budget is the configured
  * value times [[ListOperationFactor]], never above one third of the request byte limit: the
  * synthesis request carries the rendered context and a claim scaffold of the same bound, plus the
  * prompt, schema and plan. Every other operation keeps the configured value, and a configured
  * value that is tiny stays tiny, so an explicit small budget still abstains.
  */
object ContextBudget {
  val ListOperationFactor = 8
  val PersistedBundleFactor = 4
  private val listOperations = Set(QueryOperation.DirectCoauthors, QueryOperation.ShortestPath)

  /** Persisted-bundle bound. Each edge row is immutable evidence with one source reference per
    * joint work, about 3 to 4 KB, so a page of 22 coauthors is about 80 KB against the 64 KiB
    * configured bound. List operations get [[PersistedBundleFactor]] times the configured bound,
    * 262,144 bytes with the current configuration. That equals the storage default
    * `StorageConfig.maxInlineEvidenceBytes` (256 KiB, StoragePorts.scala), so a bundle at this
    * bound is still stored inline; the bound must stay at or below that value or bundles would move
    * to object storage. A configured value that is tiny stays tiny.
    */
  def persistedBundleBytes(plan: QueryPlan, config: RuntimeConfig): Int = {
    val base = config.effectiveByteLimits.persistedBundleBytes
    if (plan.operations.exists(listOperations))
      math.min(base.toLong * PersistedBundleFactor, Int.MaxValue.toLong).toInt
    else base
  }

  /** Ceiling for the claim scaffold. It carries one claim per row (about 700 bytes each), so for
    * list operations it may be twice the context ceiling; the synthesis agent also limits it to the
    * room left in the request. Other operations keep the configured context budget.
    */
  def scaffoldBytes(plan: QueryPlan, config: RuntimeConfig): Int =
    if (plan.operations.exists(listOperations)) 2 * forPlan(plan, config)
    else config.retrieval.contextTokenBudget

  def forPlan(plan: QueryPlan, config: RuntimeConfig): Int = {
    val base = config.retrieval.contextTokenBudget
    if (plan.operations.exists(listOperations)) {
      val ceiling = config.effectiveByteLimits.requestBytes / 3
      val scaled = math.min(base.toLong * ListOperationFactor, ceiling.toLong).toInt
      math.max(base, scaled)
    } else base
  }
}
