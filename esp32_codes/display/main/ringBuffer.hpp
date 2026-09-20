#ifndef RINGBUFFER_H
# define RINGBUFFER_H

# include <cstdint>
# include <cstddef>
// # include <FreeRTOS.h>
// # include <semphr.h>

template <typename T, size_t N>
class RingBuffer
{
    private:
        SemaphoreHandle_t mutex;
        uint32_t    head = 0;
        uint32_t    tail = 0;
        uint32_t    count = 0;
        bool        valid = false;
        T           *data;

    public:
        RingBuffer();
        ~RingBuffer() { free(data); };
        bool    is_valid() { return valid; }
        bool    push(const T& value);
        bool    pop(T &out);
        void    copy_data(T *dest);
        void    reset();
        size_t  size();

};

template <typename T, size_t N>
bool    RingBuffer<T, N>::push(const T& value)
{
    xSemaphoreTake(mutex, portMAX_DELAY);
    data[tail] = value;
    if (count < N) { count++; }
    else { head = (head + 1) % N; }
    tail = (tail + 1) % N;
    xSemaphoreGive(mutex);
    return true;
}

template <typename T, size_t N>
RingBuffer<T, N>::RingBuffer()
{
    data = (T*)ps_malloc(sizeof(T) * N);
    valid = (data != nullptr);
    mutex = xSemaphoreCreateMutex();
}

template <typename T, size_t N>
bool    RingBuffer<T, N>::pop(T &out)
{
    xSemaphoreTake(mutex, portMAX_DELAY);
    if (count==0) { return false; }
    out = data[head];
    head = (head + 1) % N;
    count--;
    xSemaphoreGive(mutex);
    return true;
}

template <typename T, size_t N>
size_t    RingBuffer<T, N>::size() { return N; }

template <typename T, size_t N>
void    RingBuffer<T, N>::reset()
{
    head = 0;
    tail = 0;
    count = 0;
}

template <typename T, size_t N>
void    RingBuffer<T, N>::copy_data(T *dest)
{
    xSemaphoreTake(mutex, portMAX_DELAY);
    for (size_t i = 0; i < N; i++) {
        dest[i] = data[(head + i) % N];
        // dest[i] = data[i];
    }
    xSemaphoreGive(mutex);
}

#endif