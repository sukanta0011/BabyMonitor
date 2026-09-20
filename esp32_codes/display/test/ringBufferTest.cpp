// #define CATCH_CONFIG_MAIN
// #include <catch2/catch_all.hpp>
// #include "ringBuffer.hpp"

// TEST_CASE("pop on empty buffer returns false")
// {
//     RingBuffer<int, 4> rb;
//     int out;
//     REQUIRE(rb.pop(out) == false);
// }

// TEST_CASE("push then pop preserves FIFO order")
// {
//     RingBuffer<int, 4> rb;
//     int out;
//     rb.push(1);
//     rb.push(2);
//     rb.push(3);

//     rb.pop(out);
//     REQUIRE(out == 1);
//     rb.pop(out);
//     REQUIRE(out == 2);
//     rb.pop(out);
//     REQUIRE(out == 3);
// }

// TEST_CASE("overflow evicts oldest element")
// {
//     RingBuffer<int, 4> rb;
//     int out;
//     rb.push(1);
//     rb.push(2);
//     rb.push(3);
//     rb.push(4);
//     rb.push(5);

//     rb.pop(out);
//     REQUIRE(out == 2);
// }