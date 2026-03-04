===DEBATE_TRANSCRIPT===

META:
  THREAD_ID::"2026-01-30-dogfood-virtualprovider-vs-timebudget"
  TOPIC::"For debate-hall-mcp: Should we implement VirtualProvider or time-budgeting as NEXT priority?"
  MODE::fixed
  STATUS::synthesis
  DATE::"2026-01-30"
  PURPOSE::"Dogfooding debate-hall to determine own roadmap"

PARTICIPANTS::[Wind,Wall,Door]

PROVIDERS::[
  Wind::claude-opus-4-5-20251101[PAL_clink_ideator],
  Wall::codex[PAL_clink_validator],
  Door::gemini-3-pro-preview[PAL_clink_synthesizer]
]

===TURNS===

T1::Wind[PATHOS]::{
  CONSTRAINT_ANALYSIS::[
    stated::"Choose VirtualProvider OR time-budgeting",
    hidden_dependency::"Injectable factory enables BOTH"
  ]

  CROSS_DOMAIN::[
    savepoints::PostgreSQL_nested_checkpoints,
    vcr_pattern::Ruby_VCR_HTTP_recording,
    game_snapshots::emulator_state_serialization
  ]

  THREE_PATHS::[
    obvious::VirtualProvider_first[tests_reliable_immediately],
    adjacent::injectable_factory_first[~50_lines→unlocks_both],
    heretical::VirtualProvider_IS_time_budgeting[budget_in_provider_not_orchestrator]
  ]

  GENIUS_INSIGHT::"Timeout isn't wall—it's budget. Budgets live in providers."

  QUESTIONS_FOR_WALL::[
    budget_param_breaks_protocol?,
    resume_handles_voluntary_pause?,
    any_real_provider_integration_tests?,
    combined_simpler_than_separate?,
    injectable_factory_pure_refactor?
  ]
}

T2::Wall[ETHOS]::{
  VERDICT::REQUIRES_VALIDATION

  EVIDENCE::[
    E1::providers/__init__.py:59-63→no_budget_param,
    E2::providers/cli.py:144→matches_protocol,
    E3::providers/openrouter.py:131→matches_protocol,
    E4::orchestrator.py:249→asyncio.wait_for[timeout_in_orchestrator_NOT_provider],
    E5::orchestrator.py:543→PAUSED_only_on_exceptions,
    E6::tests/e2e/→NO_real_provider_calls
  ]

  HARD_CONSTRAINTS::[
    H1::budget_param_breaks_protocol+all_providers,
    H2::orchestrator_owns_timeouts_via_asyncio.wait_for,
    H3::resume_only_for_exception_triggered_PAUSED
  ]

  FANTASY_DETECTION::[
    "budgets_live_in_providers"::VIOLATION[orchestrator.py:249_proves_otherwise]
  ]

  UNCOMFORTABLE_TRUTHS::[
    zero_real_provider_E2E_coverage,
    budget_param_is_interface_migration_not_refactor,
    orchestrator_owns_timeouts_today
  ]

  RECOMMENDED_SEQUENCE::[
    1::injectable_factory[pure_refactor_~50_lines],
    2::VirtualProvider[new_implementation_~100_lines],
    3::budget_awareness[protocol_extension_later]
  ]
}

T3::Door[LOGOS]::{
  TENSION_ANALYSIS::[
    Wind::budget_is_provider_feature,
    Wall::timeout_is_orchestrator_safeguard,
    Tension::feature_vs_safeguard
  ]

  CORE_MOVE::INVERSION_SYNTHESIS["constraint IS the solution"]

  KEY_INSIGHT::"VirtualProvider is not placeholder—it is Budget Compliance Simulator"

  THIRD_WAY::[
    implement_injectable_factory_immediately,
    use_to_inject_budget_simulating_VirtualProvider,
    provider_does_NOT_modify_protocol[satisfies_H1],
    provider_SIMULATES_budget_exhaustion[satisfies_Wind]
  ]

  EMERGENCE_PROOF::[
    Wind[budget]+Wall[VirtualProvider]→Validated_Resilience,
    Wind[factory]+Wall[immutability]→Configurable_Behavior,
    Wind[time_currency]+Wall[asyncio.wait_for]→Testable_Time
  ]

  CONCLUSION::"Not 'VirtualProvider then Budgeting' but 'Budgeting VIA VirtualProvider'"
}

===SYNTHESIS===

DECISION::"Budgeting via VirtualProvider"

IMPLEMENTATION_PRIORITY::[
  1::Injectable_Factory_Refactor[~50_lines][
    DebateOrchestrator.__init__::accepts_optional_provider_factory_Callable,
    default::create_provider_for_backward_compatibility
  ],
  2::VirtualProvider_Implementation[~100_lines][
    implements::ModelProvider_protocol,
    constructor::[delay_float,failure_mode_Literal,responses_list],
    enables::deterministic_testing_AND_budget_simulation
  ],
  3::Budget_Compliance_Tests[
    inject::VirtualProvider(delay=130),
    assert::orchestrator_handles_asyncio.TimeoutError,
    validates::orchestrator_resilience_without_flaky_tests
  ]
]

WHY_THIS_WORKS::[
  respects_protocol::no_ModelProvider.complete()_signature_change,
  enables_testing::deterministic_responses_controllable_timing,
  simulates_budgets::delay_parameter_acts_as_exhaustion_trigger,
  future_proof::factory_pattern_enables_real_budget_features_later
]

KEY_INSIGHT::"VirtualProvider doesn't just replace mocks—it defines how system should behave under budget pressure."

===END===
