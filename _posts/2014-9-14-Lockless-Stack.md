---
layout: post
title: Designing a Lock-free Stack in C++
categories:
- blog
tags: [C++, templates]
---

The post will hopefully be the first in a series on the design and implementation of lock-free data structures in C++. These structures are typically reasonably well described in literature. However, the C++11 standard allows implementations of such structures using only standard utilities. These posts are intended for readers with some familiarity with atomicity, however no prior knowledge of lock-free algorithms or the C++ atomic interface is expected.

###Lock-free Data Structures

Lock-free data structures are, as the name implies, structures which are designed without any internal locking mechanism (i.e., no mutexes, semaphores, etc.). This has several implications, the most significant of which is that such algorithms are not normally susceptible to dead-lock. Lock-free algorithms/data structures effectively guarantee that at least one thread in a multi-threaded environment is making progress at any given moment.

###Atomic Operations

C++11 introduced the `std::atomic<T>` struct for atomically operating on types. Operations on such types are free from data races. That is, if a thread reads the value of, say, a `std::atomic<int>` while another thread writes to it, the behavior is well defined. However, the standard does not require that operations on atomic types be non-blocking. All C++ atomic types (with the exception of `std::atomic_flag`) may be implemented with mutexes. Clearly, this is somewhat problematic when attempting to design lock-free data structures. Luckily, the standard also provides some mechanisms for determining whether operations on an atomic type may be blocking. These are:

1. The `is_lock_free()` member function of `std::atomic<T>`
2. The `ATOMIC_xxx_LOCK_FREE` macros

The first of these is fairly self explanatory. `std::atomic<T>` provides a member function `is_lock_free()` which will return true if the instance provides a non-blocking interface. The latter option is slightly more complex. The standard provides a series of macros which indicate the blocking grantees of the type. For example, `ATOMIC_INT_LOCK_FREE` will be defined as `0` if operations on `std::atomic<int>` will always be blocking, `1` if they may be blocking, and `2` if such operations will never be blocking. A complete list of the available macros may be found [here][macro_list].

[macro_list]: http://en.cppreference.com/w/cpp/atomic/atomic_is_lock_free

The interface for `std::atomic<T>` provides the following functions\*:

- `store`, to store an instance of `T` in this atomic variable
- `load`, to retrieve an instance of `T` from this atomic variable
- `exchange`, replace the value of `T` held by the atomic variable and return the previous value
- `is_lock_free` as previously discussed
- `operator=` equivalent to `store`
- `operator T` equivalent to `load`
- `compare_exchange_weak`/`compare_exchange_strong` these will be described in detail in a later section

_\*Additional functions are provided for certain specializations of `std::atomic`. For example, atomic integral types are specialized to have increment and decrement operations, etc._

However, merely having access to independently atomic basic operations on values (i.e., load, store, exchange) is not sufficient to construct most useful data structures. Consider, for example, an implementation of a stack using only these basic operations.

{% highlight c++ %}

template<typename T>
struct LockFreeStack {
    // Constructor and destructor...

    void push(T const& val) {
        head.store(new Node{val, head});
    }

    T pop() {
        auto retnVal = head.load()->val;
        delete head.exchange(head.load()->next);
        return retnVal;
    }

    struct Node {
        T val;
        Node* next;
    };

    std::atomic<Node*> head;
};

{% endhighlight %}
