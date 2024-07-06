@0x934efea7f017fff0;

const qux :UInt32 = 123;

struct Person {
  name @0 :Text;
  age @1 :UInt32;
  city @2 :Text;

  employment :union {
    unemployed @3 :Void;
    employer @4 :Text;
    school @5 :Text;
    selfEmployed @6 :Void;
  }
  # assume a person is only one of these
}
