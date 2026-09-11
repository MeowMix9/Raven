from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from raven.pricing.pipeline import CalculationLine, CalculationResult, PricingCalculationPipeline
from raven.pricing.resolver import PricingResolutionRequest, PricingResolver
from raven.pricing.rules import PricingRuleEvaluator


@dataclass(frozen=True, slots=True)
class QuoteCalculationRequest:
    profile_id: UUID
    as_of: date
    lines: tuple[CalculationLine, ...]
    customer_id: UUID | None = None
    product_id: UUID | None = None
    quantity: Decimal | None = None
    context: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class QuoteCalculationResult:
    pricing_profile_id: UUID
    calculation: CalculationResult


class CalculateQuote:
    """Application service that orchestrates one deterministic quote calculation."""

    def __init__(
        self,
        pricing_resolver: PricingResolver,
        pricing_repository,
        rule_evaluator: PricingRuleEvaluator | None = None,
        calculation_pipeline: PricingCalculationPipeline | None = None,
    ) -> None:
        self._pricing_resolver = pricing_resolver
        self._pricing_repository = pricing_repository
        self._rule_evaluator = rule_evaluator or PricingRuleEvaluator()
        self._calculation_pipeline = calculation_pipeline or PricingCalculationPipeline()

    def execute(self, request: QuoteCalculationRequest) -> QuoteCalculationResult:
        pricing = self._pricing_resolver.resolve(
            PricingResolutionRequest(
                profile_id=request.profile_id,
                as_of=request.as_of,
                customer_id=request.customer_id,
                product_id=request.product_id,
                quantity=request.quantity,
            )
        )
        rules = self._pricing_repository.get_rules(
            profile_id=pricing.profile_id,
            as_of=request.as_of,
        )

        context: dict[str, object] = dict(request.context or {})
        context.setdefault("quote", {})
        quote_context = context["quote"]
        if not isinstance(quote_context, dict):
            raise ValueError("Quote calculation context 'quote' must be an object")
        quote_context.setdefault("quantity", request.quantity)
        quote_context.setdefault("customer_id", request.customer_id)
        quote_context.setdefault("product_id", request.product_id)
        quote_context.setdefault("as_of", request.as_of)

        rule_result = self._rule_evaluator.evaluate(rules, context)
        calculation = self._calculation_pipeline.calculate(
            pricing,
            rule_result,
            request.lines,
        )
        return QuoteCalculationResult(
            pricing_profile_id=pricing.profile_id,
            calculation=calculation,
        )
