"""
Basic EvoForge Example: Self-Evolving Agent Architecture

Demonstrates:
- Creating initial population of agent architectures
- Running evolutionary loop with fitness evaluation
- Synthesizing knowledge from execution traces
- Skill crystallization workflow
"""

import sys
import random
import time

sys.path.insert(0, '/home/jkang/evoforge-framework')

from evoforge import (
    AgentGenome, ModuleGenome, ConnectionGenome, ModuleType, ConnectionType,
    MetaEvolutionaryCore, EvolutionConfig,
    PlannerModule, MemoryModule, SelectorModule, ExecutorModule,
    SkillCrystallizationCache, Skill, SkillState,
    ConvergentKnowledgeSynthesisEngine
)
from evoforge import ExecutionResult


def create_seed_architecture(name: str) -> AgentGenome:
    """Create a simple but functional agent architecture."""
    genome = AgentGenome(
        id=f"seed_{name}",
        name=name,
        modules=[],
        connections=[],
        generation=0
    )

    # Add essential modules
    planner = ModuleGenome(
        id="planner_1",
        type=ModuleType.PLANNER,
        name="SequentialPlanner",
        config={"strategy": "sequential"},
        parameters={"max_steps": 5}
    )
    genome.add_module(planner)

    memory = ModuleGenome(
        id="memory_1",
        type=ModuleType.MEMORY,
        name="EpisodicMemory",
        config={"memory_type": "episodic", "retrieval_strategy": "recent"},
        parameters={"max_size": 100}
    )
    genome.add_module(memory)

    selector = ModuleGenome(
        id="selector_1",
        type=ModuleType.SELECTOR,
        name="GreedySelector",
        config={"strategy": "greedy"},
        parameters={"temperature": 0.5}
    )
    genome.add_module(selector)

    executor = ModuleGenome(
        id="executor_1",
        type=ModuleType.EXECUTOR,
        name="DirectExecutor",
        config={"mode": "direct"},
        parameters={"timeout": 10, "max_retries": 3}
    )
    genome.add_module(executor)

    evaluator = ModuleGenome(
        id="evaluator_1",
        type=ModuleType.EVALUATOR,
        name="BasicEvaluator",
        config={"metrics": ["success", "efficiency"]},
        parameters={"threshold": 0.5}
    )
    genome.add_module(evaluator)

    # Define connections: sequential pipeline
    connections = [
        ConnectionGenome(
            id="conn_1",
            source_module_id=planner.id,
            target_module_id=memory.id,
            connection_type=ConnectionType.SEQUENTIAL
        ),
        ConnectionGenome(
            id="conn_2",
            source_module_id=memory.id,
            target_module_id=selector.id,
            connection_type=ConnectionType.SEQUENTIAL
        ),
        ConnectionGenome(
            id="conn_3",
            source_module_id=selector.id,
            target_module_id=executor.id,
            connection_type=ConnectionType.SEQUENTIAL
        ),
        ConnectionGenome(
            id="conn_4",
            source_module_id=executor.id,
            target_module_id=evaluator.id,
            connection_type=ConnectionType.SEQUENTIAL
        ),
    ]
    for conn in connections:
        genome.add_connection(conn)

    return genome


class SimpleFitnessEvaluator:
    """Evaluates agent fitness on simple tasks."""

    def __init__(self, tasks):
        self.tasks = tasks
        self.world_model = None  # Could integrate WorldModel for more sophisticated eval

    def evaluate(self, genome: AgentGenome) -> float:
        """
        Evaluate fitness by running the agent on sample tasks.
        Returns a composite score in [0, 1].
        """
        # In a real implementation, would instantiate modules from genome
        # and run them through tasks. Here we simulate.

        # Simulate fitness based on architectural features
        import random

        # Base score
        score = 0.5

        # Bonus for having balanced module types
        type_counts = {}
        for m in genome.modules:
            type_counts[m.type] = type_counts.get(m.type, 0) + 1

        # Having at least one of each essential type
        essentials = {ModuleType.PLANNER, ModuleType.MEMORY, ModuleType.SELECTOR, ModuleType.EXECUTOR, ModuleType.EVALUATOR}
        if all(t in type_counts for t in essentials):
            score += 0.3

        # Penalize excessive complexity for small architectures
        if len(genome.modules) > 8:
            score -= 0.1

        # Add some randomness to simulate task performance variance
        score += random.uniform(-0.1, 0.2)
        score = max(0.0, min(1.0, score))

        # Store on genome
        genome.fitness = score
        return score


def simulate_task_execution(genome: AgentGenome, task_context: dict) -> tuple:
    """
    Simulate executing a task with the given architecture.
    Returns (trace, context, success)
    """
    import time
    import random

    trace = []
    context = task_context.copy()
    context["goal"] = task_context.get("goal", "complete_task")

    # Simulate module executions
    modules = list(genome.modules)
    for i, module in enumerate(modules):
        start = time.time()
        success = random.random() > 0.2  # 80% base success
        duration = random.uniform(0.1, 2.0)

        entry = {
            "step_id": i,
            "module": module.name,
            "type": module.type.value,
            "success": success,
            "duration": duration,
            "timestamp": start,
            "error": None if success else "simulated_error"
        }
        trace.append(entry)
        time.sleep(0.01)  # Small delay

    overall_success = sum(e["success"] for e in trace) / len(trace) > 0.7
    return trace, context, overall_success


def main():
    print("="*60)
    print("EvoForge Basic Evolution Demo")
    print("="*60)

    # 1. Initialize CKSE
    print("\n[1] Initializing Convergent Knowledge Synthesis Engine...")
    ckse = ConvergentKnowledgeSynthesisEngine()
    print("✓ CKSE initialized")

    # 2. Initialize Skill Cache
    print("\n[2] Initializing Skill Crystallization Cache...")
    skill_cache = SkillCrystallizationCache()
    print("✓ Skill cache initialized")

    # 3. Create seed population
    print("\n[3] Creating seed population...")
    seed_architectures = [
        create_seed_architecture("Alpha"),
        create_seed_architecture("Beta"),
        create_seed_architecture("Gamma"),
    ]

    for arch in seed_architectures:
        print(f"  - {arch.name}: {len(arch.modules)} modules, {len(arch.connections)} connections")

    # 4. Initialize MEC
    print("\n[4] Initializing Meta-Evolutionary Core...")
    config = EvolutionConfig(
        population_size=10,
        num_generations=5,
        elite_count=2,
        tournament_size=3,
        mutation_rate=0.2,
        crossover_rate=0.7
    )

    # Simple task set for fitness evaluation
    tasks = [
        {"goal": "analyze data", "complexity": "low"},
        {"goal": "write report", "complexity": "medium"},
        {"goal": "plan project", "complexity": "high"},
    ]

    fitness_evaluator = SimpleFitnessEvaluator(tasks)
    mec = MetaEvolutionaryCore(config, fitness_evaluator)
    mec.initialize_population(seed_architectures)
    print(f"✓ MEC initialized with population size {config.population_size}")

    # 5. Run evolution
    print("\n[5] Running evolutionary loop...")
    print("-"*60)

    for gen in range(3):  # Just 3 generations for demo
        print(f"\nGeneration {gen}:")

        # Evaluate population (fitness_evaluator.evaluate called inside evolve_generation)
        # Collect traces from each genome's evaluation
        traces_batch = []
        for genome in mec.population[:5]:  # Sample top 5 for trace collection
            task = random.choice(tasks)
            trace, ctx, success = simulate_task_execution(genome, task)
            traces_batch.append((trace, ctx, genome))

        # Process traces through CKSE
        if traces_batch:
            new_knowledge = ckse.process_traces(traces_batch)
            print(f"  Synthesized {len(new_knowledge)} new knowledge units")

            # Apply knowledge-guided mutations
            for genome in mec.population:
                hints = ckse.get_mutation_hints(genome)
                if hints:
                    # In real implementation, these hints would guide mutation
                    pass

        # Evolve one generation
        stats = mec.evolve_generation()
        print(f"  Best fitness: {stats['best_fitness']:.4f}")
        print(f"  Avg fitness: {stats['avg_fitness']:.4f}")
        print(f"  Avg modules: {stats['avg_modules']:.1f}")

    # 6. Demonstrate skill crystallization
    print("\n[6] Skill Crystallization Workflow...")
    print("-"*60)

    # Create a sample skill from a module
    sample_module = PlannerModule.create({
        "strategy": "sequential",
        "max_steps": 5
    })

    skill = skill_cache.register_skill(
        name="SequentialPlanningSkill",
        description="Plans tasks as sequential steps",
        module=sample_module,
        domain="planning",
        tags=["planning", "sequential"]
    )
    print(f"Registered skill: {skill.name} (state: {skill.state.value})")

    # Simulate executions to build telemetry
    print("Simulating executions...")
    for i in range(10):
        context = {"goal": f"task_{i}"}
        start = time.time()
        result = sample_module.execute(context)
        duration = (time.time() - start) * 1000

        execution = skill.record_execution(context, result, duration)
        print(f"  Execution {i+1}: {'success' if result.success else 'fail'}")

    print(f"Skill metrics after 10 executions:")
    print(f"  Total: {skill.metrics.total_executions}")
    print(f"  Success rate: {skill.metrics.success_rate:.1%}")
    print(f"  State: {skill.state.value}")

    # 7. Summary
    print("\n" + "="*60)
    print("Demo Complete!")
    print("="*60)
    print("\nKey achievements:")
    print(f"  - Evolved {mec.generation} generations")
    print(f"  - Best fitness: {mec.get_best_genome(1)[0].fitness:.4f}")
    print(f"  - Knowledge units: {len(ckse.synthesizer.knowledge_store)}")
    print(f"  - Skills in cache: {len(skill_cache.skills)}")

    print("\nNext steps:")
    print("  - Integrate real LLM-backend for planning/execution")
    print("  - Implement actual fitness evaluation on real tasks")
    print("  - Add OpenRouter API integration")
    print("  - Build web dashboard for monitoring evolution")

    return 0


if __name__ == "__main__":
    import random
    exit(main())
