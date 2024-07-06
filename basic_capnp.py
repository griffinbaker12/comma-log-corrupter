import capnp
import person_capnp  # type: ignore (import hook magic...)

# Test default value
print("qux is:", person_capnp.qux)

# Create a new message and get the root
person = person_capnp.Person.new_message()
person.name = "Alice"
person.age = 12
person.city = "NY"
person.employment.school = "MIT"

which = person.employment.which()
if which == "unemployed":
    print("unemployed")
elif which == "employer":
    print("employer:", person.employment.employer)
elif which == "school":
    print("student at:", person.employment.school)
elif which == "selfEmployed":
    print("self employed")

# Serialize the message to bytes
serialized_data = person.to_bytes()
person = person_capnp.Person.from_bytes(serialized_data)
print("k,v pais in the person")
for k, v in person.__dict__.items():
    print(k, v)
    print()
with person as p:
    print(p)
