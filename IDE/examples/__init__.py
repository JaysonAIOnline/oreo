"""
OREO Example Programs
Example programs demonstrating the language features.
"""

# Example 1: Hello World
HELLO_WORLD = """
define function main
  call print "Hello, World!"
"""

# Example 2: Factorial
FACTORIAL = """
define function factorial(n: Int) -> Int
  if n <= 1 then
    return 1
  else
    return n * factorial(n - 1)

define function main
  var result = factorial(5)
  call print result
"""

# Example 3: Fibonacci
FIBONACCI = """
define function fib(n: Int) -> Int
  if n <= 1 then
    return n
  else
    return fib(n - 1) + fib(n - 2)

define function main
  for i in 0..10
    call print fib(i)
"""

# Example 4: File I/O
FILE_IO = """
define function read_file(path: String) -> String
  var handle = call open(path, "r")
  var content = call read_all(handle)
  call close(handle)
  return content

define function write_file(path: String, content: String) -> Unit
  var handle = call open(path, "w")
  call write(handle, content)
  call close(handle)

define function main
  call write_file("test.txt", "Hello from OREO!")
  var content = call read_file("test.txt")
  call print content
"""

# Example 5: HTTP Server (conceptual)
HTTP_SERVER = """
define function handle_request(req: Request) -> Response
  if req.path == "/" then
    return Response(200, "text/html", "<h1>Hello OREO!</h1>")
  else
    return Response(404, "text/plain", "Not Found")

define function main
  var server = call create_server(8080, handle_request)
  call server.start()
  call print "Server running on http://localhost:8080"
"""

# Example 6: Concurrent Processing
CONCURRENT = """
define function process_item(item: Int) -> Int
  call sleep(100)  // Simulate work
  return item * 2

define function main
  var items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
  
  parallel
    var results = []
    for item in items
      results.append(process_item(item))
    return results
  
  call print "All done!"
"""

# Example 7: Type Definitions
TYPES_DEMO = """
define record Person
  name: String
  age: Int
  email: String

define sum Result
  Ok(value: Int)
  Err(error: String)

define function divide(a: Int, b: Int) -> Result
  if b == 0 then
    return Err("Division by zero")
  else
    return Ok(a / b)

define function main
  var person = Person("Alice", 30, "alice@example.com")
  call print person.name
  
  var result = divide(10, 2)
  match result
    Ok(value) -> call print "Result: " + value
    Err(error) -> call print "Error: " + error
"""

# Example 8: Effects
EFFECTS_DEMO = """
define function read_config() -> String [IO]
  var content = call read_file("config.json")
  return content

define function update_state(key: String, value: Int) -> Unit [State]
  call state_set(key, value)

define function main [IO, State]
  var config = call read_config()
  call update_state("last_config", config.length)
  call print "Config loaded"
"""

# Example 9: Contracts
CONTRACTS_DEMO = """
define function sqrt(x: Int) -> Int
  requires x >= 0
  ensures result * result <= x and (result + 1) * (result + 1) > x
  
  var guess = x / 2
  while guess * guess > x
    guess = (guess + x / guess) / 2
  return guess

define function main
  var result = call sqrt(16)
  call print result  // Should print 4
"""

# Example 10: Higher-Order Functions
HIGHER_ORDER = """
define function map(arr: Array<Int>, f: Fn(Int) -> Int) -> Array<Int>
  var result = []
  for item in arr
    result.append(call f(item))
  return result

define function double(x: Int) -> Int
  return x * 2

define function main
  var numbers = [1, 2, 3, 4, 5]
  var doubled = call map(numbers, double)
  call print doubled  // Should print [2, 4, 6, 8, 10]
"""

# All examples
EXAMPLES = {
    "hello_world": HELLO_WORLD,
    "factorial": FACTORIAL,
    "fibonacci": FIBONACCI,
    "file_io": FILE_IO,
    "http_server": HTTP_SERVER,
    "concurrent": CONCURRENT,
    "types_demo": TYPES_DEMO,
    "effects_demo": EFFECTS_DEMO,
    "contracts_demo": CONTRACTS_DEMO,
    "higher_order": HIGHER_ORDER,
}


def get_example(name: str) -> str:
    """Get example by name."""
    return EXAMPLES.get(name, "")


def list_examples() -> List[str]:
    """List all example names."""
    return list(EXAMPLES.keys())