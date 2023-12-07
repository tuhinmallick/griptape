import pytest

from griptape.artifacts import TextArtifact
from griptape.memory.task.storage import TextArtifactStorage
from griptape.rules import Rule, Ruleset
from griptape.tokenizers import OpenAiTokenizer
from griptape.tasks import PromptTask, BaseTask, ToolkitTask
from griptape.memory.structure import ConversationMemory
from tests.mocks.mock_prompt_driver import MockPromptDriver
from griptape.structures import Pipeline
from tests.mocks.mock_tool.tool import MockTool
from tests.unit.structures.test_agent import MockEmbeddingDriver


class TestPipeline:
    def test_init(self):
        driver = MockPromptDriver()
        pipeline = Pipeline(prompt_driver=driver, rulesets=[Ruleset("TestRuleset", [Rule("test")])])

        assert pipeline.prompt_driver is driver
        assert pipeline.input_task is None
        assert pipeline.output_task is None
        assert pipeline.rulesets[0].name == "TestRuleset"
        assert pipeline.rulesets[0].rules[0].value == "test"
        assert pipeline.conversation_memory is not None

    def test_rulesets(self):
        pipeline = Pipeline(rulesets=[Ruleset("Foo", [Rule("foo test")])])

        pipeline.add_tasks(
            PromptTask(rulesets=[Ruleset("Bar", [Rule("bar test")])]),
            PromptTask(rulesets=[Ruleset("Baz", [Rule("baz test")])]),
        )

        assert isinstance(pipeline.tasks[0], PromptTask)
        assert len(pipeline.tasks[0].all_rulesets) == 2
        assert pipeline.tasks[0].all_rulesets[0].name == "Foo"
        assert pipeline.tasks[0].all_rulesets[1].name == "Bar"

        assert isinstance(pipeline.tasks[1], PromptTask)
        assert len(pipeline.tasks[1].all_rulesets) == 2
        assert pipeline.tasks[1].all_rulesets[0].name == "Foo"
        assert pipeline.tasks[1].all_rulesets[1].name == "Baz"

    def test_rules(self):
        pipeline = Pipeline(rules=[Rule("foo test")])

        pipeline.add_tasks(PromptTask(rules=[Rule("bar test")]), PromptTask(rules=[Rule("baz test")]))

        assert isinstance(pipeline.tasks[0], PromptTask)
        assert len(pipeline.tasks[0].all_rulesets) == 2
        assert pipeline.tasks[0].all_rulesets[0].name == "Default Ruleset"
        assert pipeline.tasks[0].all_rulesets[1].name == "Additional Ruleset"

        assert isinstance(pipeline.tasks[1], PromptTask)
        assert pipeline.tasks[1].all_rulesets[0].name == "Default Ruleset"
        assert pipeline.tasks[1].all_rulesets[1].name == "Additional Ruleset"

    def test_rules_and_rulesets(self):
        with pytest.raises(ValueError):
            Pipeline(rules=[Rule("foo test")], rulesets=[Ruleset("Bar", [Rule("bar test")])])

        with pytest.raises(ValueError):
            pipeline = Pipeline()
            pipeline.add_task(PromptTask(rules=[Rule("foo test")], rulesets=[Ruleset("Bar", [Rule("bar test")])]))

    def test_with_default_task_memory(self):
        pipeline = Pipeline()

        pipeline.add_task(ToolkitTask(tools=[MockTool()]))

        assert isinstance(pipeline.tasks[0], ToolkitTask)
        assert pipeline.tasks[0].task_memory == pipeline.task_memory
        assert pipeline.tasks[0].tools[0].input_memory is not None
        assert pipeline.tasks[0].tools[0].input_memory[0] == pipeline.task_memory
        assert pipeline.tasks[0].tools[0].output_memory is not None
        assert pipeline.tasks[0].tools[0].output_memory["test"][0] == pipeline.task_memory

    def test_embedding_driver(self):
        embedding_driver = MockEmbeddingDriver()
        pipeline = Pipeline(embedding_driver=embedding_driver)

        pipeline.add_task(ToolkitTask(tools=[MockTool()]))

        storage = list(pipeline.task_memory.artifact_storages.values())[0]
        assert isinstance(storage, TextArtifactStorage)
        memory_embedding_driver = storage.query_engine.vector_store_driver.embedding_driver

        assert memory_embedding_driver == embedding_driver

    def test_with_default_task_memory_and_empty_tool_output_memory(self):
        pipeline = Pipeline()

        pipeline.add_task(ToolkitTask(tools=[MockTool(output_memory={})]))

        assert isinstance(pipeline.tasks[0], ToolkitTask)
        assert pipeline.tasks[0].tools[0].output_memory == {}

    def test_without_default_task_memory(self):
        pipeline = Pipeline(task_memory=None)

        pipeline.add_task(ToolkitTask(tools=[MockTool()]))

        assert isinstance(pipeline.tasks[0], ToolkitTask)
        assert pipeline.tasks[0].tools[0].input_memory is None
        assert pipeline.tasks[0].tools[0].output_memory is None

    def test_with_memory(self):
        first_task = PromptTask("test1")
        second_task = PromptTask("test2")
        third_task = PromptTask("test3")

        pipeline = Pipeline(prompt_driver=MockPromptDriver(), conversation_memory=ConversationMemory())

        pipeline + [first_task, second_task, third_task]

        assert pipeline.conversation_memory is not None
        assert len(pipeline.conversation_memory.runs) == 0

        pipeline.run()
        pipeline.run()
        pipeline.run()

        assert len(pipeline.conversation_memory.runs) == 3

    def test_tasks_initialization(self):
        first_task = PromptTask(id="test1")
        second_task = PromptTask(id="test2")
        third_task = PromptTask(id="test3")
        pipeline = Pipeline(tasks=[first_task, second_task, third_task])

        assert len(pipeline.tasks) == 3
        assert pipeline.tasks[0].id == "test1"
        assert pipeline.tasks[1].id == "test2"
        assert pipeline.tasks[2].id == "test3"
        assert len(first_task.parents) == 0
        assert len(first_task.children) == 1
        assert len(second_task.parents) == 1
        assert len(second_task.children) == 1
        assert len(third_task.parents) == 1
        assert len(third_task.children) == 0

    def test_tasks_order(self):
        first_task = PromptTask("test1")
        second_task = PromptTask("test2")
        third_task = PromptTask("test3")

        pipeline = Pipeline(prompt_driver=MockPromptDriver())

        pipeline + first_task
        pipeline + second_task
        pipeline + third_task

        assert pipeline.input_task.id is first_task.id
        assert pipeline.tasks[1].id is second_task.id
        assert pipeline.tasks[2].id is third_task.id
        assert pipeline.output_task.id is third_task.id

    def test_add_task(self):
        first_task = PromptTask("test1")
        second_task = PromptTask("test2")

        pipeline = Pipeline(prompt_driver=MockPromptDriver())

        pipeline + first_task
        pipeline + second_task

        assert len(pipeline.tasks) == 2
        assert first_task in pipeline.tasks
        assert second_task in pipeline.tasks
        assert first_task.structure == pipeline
        assert second_task.structure == pipeline
        assert len(first_task.parents) == 0
        assert len(first_task.children) == 1
        assert len(second_task.parents) == 1
        assert len(second_task.children) == 0

    def test_add_tasks(self):
        first_task = PromptTask("test1")
        second_task = PromptTask("test2")

        pipeline = Pipeline(prompt_driver=MockPromptDriver())

        pipeline + [first_task, second_task]

        assert len(pipeline.tasks) == 2
        assert first_task in pipeline.tasks
        assert second_task in pipeline.tasks
        assert first_task.structure == pipeline
        assert second_task.structure == pipeline
        assert len(first_task.parents) == 0
        assert len(first_task.children) == 1
        assert len(second_task.parents) == 1
        assert len(second_task.children) == 0

    def test_insert_task_in_middle(self):
        first_task = PromptTask("test1", id="test1")
        second_task = PromptTask("test2", id="test2")
        third_task = PromptTask("test3", id="test3")

        pipeline = Pipeline(prompt_driver=MockPromptDriver())

        pipeline + [first_task, second_task]
        pipeline.insert_task(first_task, third_task)

        assert len(pipeline.tasks) == 3
        assert first_task in pipeline.tasks
        assert second_task in pipeline.tasks
        assert third_task in pipeline.tasks
        assert first_task.structure == pipeline
        assert second_task.structure == pipeline
        assert third_task.structure == pipeline
        assert not [parent.id for parent in first_task.parents]
        assert [child.id for child in first_task.children] == ["test3"]
        assert [parent.id for parent in second_task.parents] == ["test3"]
        assert not [child.id for child in second_task.children]
        assert [parent.id for parent in third_task.parents] == ["test1"]
        assert [child.id for child in third_task.children] == ["test2"]

    def test_insert_task_at_end(self):
        first_task = PromptTask("test1", id="test1")
        second_task = PromptTask("test2", id="test2")
        third_task = PromptTask("test3", id="test3")

        pipeline = Pipeline(prompt_driver=MockPromptDriver())

        pipeline + [first_task, second_task]
        pipeline.insert_task(second_task, third_task)

        assert len(pipeline.tasks) == 3
        assert first_task in pipeline.tasks
        assert second_task in pipeline.tasks
        assert third_task in pipeline.tasks
        assert first_task.structure == pipeline
        assert second_task.structure == pipeline
        assert third_task.structure == pipeline
        assert not [parent.id for parent in first_task.parents]
        assert [child.id for child in first_task.children] == ["test2"]
        assert [parent.id for parent in second_task.parents] == ["test1"]
        assert [child.id for child in second_task.children] == ["test3"]
        assert [parent.id for parent in third_task.parents] == ["test2"]
        assert not [child.id for child in third_task.children]

    def test_prompt_stack_without_memory(self):
        pipeline = Pipeline(conversation_memory=None, prompt_driver=MockPromptDriver())

        task1 = PromptTask("test")
        task2 = PromptTask("test")

        pipeline.add_tasks(task1, task2)

        assert len(task1.prompt_stack.inputs) == 2
        assert len(task2.prompt_stack.inputs) == 2

        pipeline.run()

        assert len(task1.prompt_stack.inputs) == 3
        assert len(task2.prompt_stack.inputs) == 3

        pipeline.run()

        assert len(task1.prompt_stack.inputs) == 3
        assert len(task2.prompt_stack.inputs) == 3

    def test_prompt_stack_with_memory(self):
        pipeline = Pipeline(prompt_driver=MockPromptDriver())

        task1 = PromptTask("test")
        task2 = PromptTask("test")

        pipeline.add_tasks(task1, task2)

        assert len(task1.prompt_stack.inputs) == 2
        assert len(task2.prompt_stack.inputs) == 2

        pipeline.run()

        assert len(task1.prompt_stack.inputs) == 5
        assert len(task2.prompt_stack.inputs) == 5

        pipeline.run()

        assert len(task1.prompt_stack.inputs) == 7
        assert len(task2.prompt_stack.inputs) == 7

    def test_text_artifact_token_count(self):
        text = "foobar"

        assert TextArtifact(text).token_count(
            OpenAiTokenizer(model=OpenAiTokenizer.DEFAULT_OPENAI_GPT_3_CHAT_MODEL)
        ) == OpenAiTokenizer(model=OpenAiTokenizer.DEFAULT_OPENAI_GPT_3_CHAT_MODEL).count_tokens(text)

    def test_run(self):
        task = PromptTask("test")
        pipeline = Pipeline(prompt_driver=MockPromptDriver())
        pipeline + task

        assert task.state == BaseTask.State.PENDING

        result = pipeline.run()

        assert "mock output" in result.output_task.output.to_text()
        assert task.state == BaseTask.State.FINISHED

    def test_run_with_args(self):
        task = PromptTask("{{ args[0] }}-{{ args[1] }}")
        pipeline = Pipeline(prompt_driver=MockPromptDriver())
        pipeline + [task]

        pipeline._execution_args = ("test1", "test2")

        assert task.input.to_text() == "test1-test2"

        pipeline.run()

        assert task.input.to_text() == "-"

    def test_context(self):
        parent = PromptTask("parent")
        task = PromptTask("test")
        child = PromptTask("child")
        pipeline = Pipeline(prompt_driver=MockPromptDriver())

        pipeline + [parent, task, child]

        context = pipeline.context(task)

        assert context["parent_output"] is None

        pipeline.run()

        context = pipeline.context(task)

        assert context["parent_output"] == parent.output.to_text()
        assert context["structure"] == pipeline
        assert context["parent"] == parent
        assert context["child"] == child
