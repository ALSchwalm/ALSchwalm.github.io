---
layout: post
title: Designing a Lock-free Stack in C++
categories:
- blog
tags: [C++, templates, lockfree]
---

The post will be the first in a series on the design and implementation of lock-free data structures in C++. These structures are typically reasonably well described in literature. However, the C++11 standard allows implementations of such structures using only standard utilities. These posts are intended for readers with some familiarity with atomicity, however no prior knowledge of lock-free algorithms or the C++ atomic interface is expected.

###Lock-free Data Structures

Lock-free data structures are, as the name implies, structures which are designed without any internal locking mechanism (i.e., no mutexes, semaphores, etc.). This has several implications, the most significant of which is that such algorithms are not normally susceptible to deadlock. Lock-free algorithms/data structures effectively guarantee that at least one thread in a multi-threaded environment is making progress at any given moment.

In addition to avoiding deadlock, lock-free structures may also provide significant performance gains in situations where there is relatively little contention.

###C++ Atomic Types

C++11 introduced the `std::atomic<T>` struct for atomically operating on types. Operations on such types are guaranteed to be free from data races. So if a thread reads the value of, say, a `std::atomic<int>` while another thread writes to it, the behavior is well defined. The interface for `std::atomic<T>` provides the following functions\*:

| Function Name             | Description                                                            |
|---------------------------+------------------------------------------------------------------------|
| `store`                   | store an instance of `T` in this atomic variable                       |
| `load`                    | retrieve an instance of `T` from this atomic variable                  |
| `exchange`                | replace the value in the atomic variable and return the previous value |
| `is_lock_free`            | discussed below                                                        |
| `operator=`               | equivalent to `store`                                                  |
| `operator T`              | equivalent to `load`                                                   |
| `compare_exchange_strong` |                                                                        |
| `compare_exchange_weak`   | these will be described in detail in a later section                   |

_\*Additional functions are provided for certain specializations of `std::atomic`. For example, atomic integral types are specialized to have increment and decrement operators, etc._

 However, the standard does not require that operations on atomic types be non-blocking. All C++ atomic types (with the exception of `std::atomic_flag`) may be implemented with mutexes. Clearly, this is somewhat problematic when attempting to design lock-free data structures. Handily, the standard also provides some mechanisms for determining whether operations on an atomic type may be blocking. These are:

1. The `is_lock_free()` member function of `std::atomic<T>`
2. The `ATOMIC_xxx_LOCK_FREE` macros

The first of these is fairly self explanatory. `std::atomic<T>` provides a member function `is_lock_free()` which will return true if the instance provides a non-blocking interface. The latter option is slightly more complex. The standard provides a series of macros which indicate the blocking grantees of a given type. For example, `ATOMIC_INT_LOCK_FREE` will be defined as `0` if operations on `std::atomic<int>` will always be blocking, `1` if they may be blocking, and `2` if such operations will never be blocking. A complete list of the available macros may be found [here][macro_list].

[macro_list]: http://en.cppreference.com/w/cpp/atomic/atomic_is_lock_free

###Implementation Using Basic Operations

However, merely having access to independently atomic basic operations on values (i.e., load, store, and exchange) is not sufficient to construct most useful data structures. Consider, for example, an implementation of a stack using only these basic operations:

{% highlight c++ linenos=table %}

template<typename T>
struct LockFreeStack {
    // Constructor and destructor...

    void push(T const& val) {
        head.store(new Node{val, head});
    }

    T pop() {
        auto val = head.load()->val;
        delete head.exchange(head.load()->next);
        return val;
    }

    struct Node {
        T val;
        Node* next;
    };

    std::atomic<Node*> head;
};

{% endhighlight %}

There are several problems with the implementation of `pop()`. The two calls to `head.load()` are not guaranteed to return he same value. A different thread may have popped a value off of the stack in between these calls, causing an effective duplication of values. Additionally, between loading the value of `next` and the execution of the `exchange` in line 11, a different thread may have pushed a value, which will be lost after the exchange. Similar problems exist with the implementation of `push()`.

The design of more complex data structures requires the ability to do slightly more work in an atomic operation than any of `load`, `store` or `exchange`. Enter: compare-and-swap.

###Compare-and-swap

Atomic compare-and-swap (CAS) is an function which effectively performs the following steps in an atomic fashion:

{% highlight c++ linenos=table %}

template<typename T>
bool CAS(std::atomic<T>& target, T& expected, T update) {
    if (target == expected) {
        target = update;
        return true;
    } else {
        expected = target;
        return false;
    }
}

{% endhighlight %}

That is, CAS checks for an expected value, updating a target atomic variable if it contains the expected value. Otherwise the expected value is set to the current value of the target. CAS is commonly used in the following general pattern:

1. Copy the current value of some atomic variable
2. Perform some work, assuming the original variable will not change
3. CAS the updated value into the target (if it has actually not changed)
4. If the CAS fails, go to 1, otherwise done

This pattern is what guarantees that some thread will be making progress at any given moment. It must be the case that _some_ thread's assumption is correct, and that thread's CAS will succeed.

CAS is spelled `compare_exchange_weak`* in C++. Using this pattern, `pop()` may be redesigned as follows:

_\*The difference between `compare_exchange_weak` and `compare_exchange_strong` is that the former allows for spurious failures but is potentially faster. If the function is going to be called in a loop anyway, `compare_exchange_weak` is the preferred choice._

{% highlight c++ linenos=table %}
T pop() {
    // Get an initial value for head
    Node* oldHead = head.load();
    Node* newHead;
    do {
        // Make the new head equal the old head's next
        newHead = oldHead->next;

    // CAS the next into head
    } while (!head.compare_exchange_weak(oldHead, newHead));

    auto val = oldHead->val;
    delete oldHead;
    return val;
}

{% endhighlight %}

This implementation performs some work (reading `next`), under the assumption that `head` will not change. If it has actually not changed, the value of `head` is set to `newHead`. If the value of `head` has changed (i.e., some other thread has pushed/popped) then `oldHead` will be set to the current value of `head` and execution returns to the beginning of the loop.

Making use of a similar pattern, `push` becomes:

{% highlight c++ linenos=table %}

void push(T const& val) {
    // Construct a new node and set its next to the current head
    auto newNode = new Node{val, head};

    // CAS the new node in to head
    while (!head.compare_exchange_weak(newNode->next, newNode)){}
}

{% endhighlight %}

In this implementation the 'work' step is somewhat hidden. Remember, however, that the 'expected' value (i.e., the first parameter to `compare_exchange_weak`) will be updated if the CAS fails. This is the 'work' phase in this function.
