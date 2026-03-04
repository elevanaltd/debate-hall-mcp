===DEBATE_TRANSCRIPT===

META:
  THREAD_ID::"2026-01-30-rundebate-reliability-analysis"
  TOPIC::"How can we make run_debate more reliable and testable? Consider: provider timeouts, error handling, testing strategies, and alternative configurations."
  MODE::fixed
  STATUS::synthesis
  TURN_COUNT::5
  DATE::"2026-01-30"

PARTICIPANTS::[Wind,Wall,Door]

TIMING::[
  Wind::~97s[PAL_clink_claude],
  Wall::~10min[codex_CLI],
  Door::~1min[gemini_CLI],
  Total::~14min
]

===TURNS===

T1::Wind[PATHOS]::{
  CONSTRAINT_ANALYSIS::[
    CLI_slow::300s_timeout_×_3_providers_→_15min_worst,
    3_CLIs::different_failure_modes,
    No_integration_tests::mocked_at_create_provider,
    Timeouts::symptom_not_disease
  ]

  CROSS_DOMAIN::[
    circuit_breaker::track_health_fallback,
    replay_debugging::record_responses_VCR,
    chaos_engineering::inject_failures,
    progressive_delivery::nightly_real_tests
  ]

  PATHS::[
    obvious::[test_tier_openrouter,VCR_fixtures,correlation_IDs],
    adjacent::[RecordingProvider,DeterministicProvider,test_pyramid],
    heretical::[event_driven_state_machine,async_handles,pure_functions]
  ]

  INSIGHT::"PAUSED state exists because providers unreliable. Embrace as normal flow."
  REFRAME::"Debate is eventually-consistent process, not sync operation"

  QUESTIONS::[MCP_non_blocking?,models_vs_prompts?,chaos_coverage?,max_duration?]
}

T2::Wall[ETHOS]::{
  VERDICT::CONDITIONAL_GO

  EVIDENCE::[
    E1::tools/orchestrate.py:95→run_debate_synchronous,
    E2::orchestrator.py:249→asyncio.wait_for(timeout),
    E3::orchestrator.py:55→DEFAULT_PROVIDER_TIMEOUT=300s,
    E4::providers/cli.py:23→CLI_timeout=120s[CONFLICT!],
    E5::providers/__init__.py:47→ModelProvider_Protocol,
    E6::orchestrator.py:543,552→PAUSED_on_failure
  ]

  HARD_CONSTRAINTS::[
    H1::run_debate_synchronous→async_needs_arch_change,
    H2::CLI_120s_vs_orchestrator_300s[CONFLICT],
    H3::no_get_events_tool→no_polling,
    H4::max_turns/max_rounds_enforced
  ]

  FANTASY_DETECTION::[
    "MCP non-blocking"::MISSING_EVIDENCE,
    "CLI 300s timeout"::VIOLATION[actual=120s]
  ]

  UNCOMFORTABLE_TRUTHS::[
    timeout_conflict_120s_vs_300s,
    no_real_provider_integration_tests,
    async_architecture_not_surfaced
  ]
}

T3::Door[LOGOS]::{
  TENSIONS::[
    mock_vs_reality::Speed_vs_Fidelity,
    async_vs_sync::Architecture_vs_Environment,
    tests_vs_system::Verification_vs_Robustness
  ]

  EMERGENT_PATH::"Budgeted Latent Orchestration"

  KEY_INSIGHT::"120s CLI timeout isn't failure to avoid—it's Time Budget to manage"

  THIRD_WAY::[
    orchestrator_accepts_time_budget,
    runs_until_budget_low,
    voluntarily_checkpoints→PAUSED,
    satisfies_Wind_async+Wall_sync
  ]

  EMERGENCE_PROOF::[
    Wind[Virtual]+Wall[Abstraction]→Injectable_Provider_Factory,
    Wind[Async]+Wall[Timeout]→Voluntary_Suspension,
    Wind[TestTier]+Wall[Validation]→Dual_Mode_CI
  ]

  IMPLEMENTATION::[
    1::provider_factory_injection,
    2::time_budgeting_with_voluntary_pause,
    3::VirtualProvider[Replay,Deterministic,FaultInjection]
  ]
}

T4::Wind[APPROVAL]::{
  VERDICT::APPROVED
  RESONATES::[
    event_driven→time_budgeting::preserves_sync_API,
    virtualization→injectable_factory::clean_DI,
    test_pyramid→dual_mode_CI::pragmatic
  ]
  INSIGHT::"Timeouts aren't failures to handle—they're budgets to manage"
}

T5::Wall[APPROVAL]::{
  VERDICT::APPROVED_WITH_CONDITIONS
  SATISFIED::[H1,H2,H3,H4]
  CONDITIONS::[
    time_budget_configurable_per_tier,
    VirtualProvider_same_interface_tests,
    docs_clarify_pause_vs_failure
  ]
}

===SYNTHESIS===

CONSENSUS::ACHIEVED

ARCHITECTURE_DECISIONS::[
  ADR1::Injectable_Provider_Factory[
    orchestrator_accepts_provider_factory_callable,
    enables_virtualization+chaos+dry_run,
    backward_compatible
  ],
  ADR2::Time_Budget_Execution[
    max_execution_time_parameter[default=100s],
    voluntary_pause_before_timeout,
    returns_PAUSED_with_continuation,
    solves_timeout_conflict
  ],
  ADR3::Virtual_Provider[
    conforms_ModelProvider_protocol,
    modes::[Replay,Deterministic,FaultInjection],
    enables_fast_CI
  ],
  ADR4::Dual_Mode_CI[
    fast::VirtualProvider+infinite_budget,
    validation::real_providers+resumption
  ]
]

IMPLEMENTATION_PRIORITY::[
  1::fix_timeout_conflict[CLI_120s_vs_orchestrator_300s],
  2::injectable_provider_factory,
  3::time_budgeting_with_voluntary_suspension,
  4::VirtualProvider_for_testing,
  5::dual_mode_CI
]

KEY_INSIGHT::"Timeouts aren't failures to handle—they're budgets to manage. Long debates become sequences of short, reliable bursts."

===END===
