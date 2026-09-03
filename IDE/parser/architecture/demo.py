from parser.architecture.parser import dumps
from parser.architecture.runtime import GraphRuntime

SAMPLES = [
    "I need a db, three pages and a couple of includes.",
    "Connect the db to the landing page with a secure auth.",
    "Make all pages include Header and Footer.",
    "Handshake the dashboard to the db with secure auth.",
    "Show me everything that connects to MainDB.",
    "What would break if I delete Header?",
    "Pages missing a database",
    "Remove the connection between Settings and MainDB.",
]


def main() -> None:
    runtime = GraphRuntime(use_llm=True)
    for sample in SAMPLES:
        result = runtime.say(sample)
        print("=" * 72)
        print("IN :", sample)
        print("INT:", [i["action"] for i in result["intents"]])
        print(result["ascii"])
        print()
    print("FINAL SNAPSHOT")
    print(dumps(runtime.graph.snapshot()))


if __name__ == "__main__":
    main()
