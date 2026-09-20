#include <iostream>
#include <string>
#include <vector>

const int BUFFER_SIZE = 25;  // tiny, on purpose, to force overflow fast
char ring[BUFFER_SIZE];
int head = 0, tail = 0, count = 0;

void push(char c) {
    ring[tail] = c;
    if (count < BUFFER_SIZE) count++;
    else head = (head + 1) % BUFFER_SIZE;
    tail = (tail + 1) % BUFFER_SIZE;
}

int main() {
    // Simulate a burst: two frames arriving back-to-back, no extraction in between
    std::string burst = "F1[aaaaaaaa]F2[bbbbbbbb]F3[cccccccc]";

    std::cout << "Simulating read_from_stream() — pushing entire burst first:\n";
    for (char c : burst) {
        push(c);
    }

    std::cout << "Buffer contents after the WHOLE burst (before any extraction):\n";
    for (int i = 0; i < count; i++) {
        std::cout << ring[(head + i) % BUFFER_SIZE];
    }
    std::cout << "\n\n";
}