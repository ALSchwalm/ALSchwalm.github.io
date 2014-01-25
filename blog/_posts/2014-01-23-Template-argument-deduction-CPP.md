---
layout: post
title: Getting the most from Template Argument Deduction in C++
categories:
- C++ templates
---

Let me preface this post by saying that the rules regarding template argument
deduction in C++ are varied and somewhat complex. I will not attempt to describe
them in their entirety in the confines of this short post. I leave that cumbersome
task to more eloquent and knowledgeable programmers.

That being said, template argument deduction is a very useful feature of the language
which has an unfortunate tendency to be underutilized. For the unfamiliar,
C++ function templates have the ability to determine the types upon which they are
specialized from the types of the arguments passed to the function. For example:

{% highlight c++ %}

template<typename T>
T transmogrify(T t){...}

{% endhighlight %}

If the above function is called with `transmogrify<char>('a')`, everything
will work as expected. The specialization `transmogrify<char>` accepts an argument of
type `char` because `T = char`. However, C++ makes this easier for you. The
compiler can deduce the type. So merely calling `transmogrify('a')` is sufficient
information for the compiler to determine the type of `T`.

The utility of this cannot be overstated. As boring, fallible humans, we are likely
to make mistakes. And, if you're anything like me, you probably tend to make quite a
few.

Now suppose I, thinking myself above the petty knowledge of the compiler, specify
the type of `T` manually by calling `transmogrify<std::string>("cats")`. This will
compile and (let us suppose) work as intended. But what would happen if we let the
compiler deduce the type? The type of a string literal in C++ is `const char[]`, so
the function specialization would look like `transmogrify<const char[]>(const
char[])`, and calling it would look like `transmogrify("cats")`. The important thing
to note here is that a call to the latter function does not create a pointless
`std::string`. It is also shorter and (in my opinion) cleaner. Indeed, the caller
need not even know that the function is a template function.

This deduction also works for template class arguments. That is, in the following
sample

{% highlight c++ %}

template<typename T, size_t size>
void locate(const std::array<T, size>& arr, const T& item){...}
...
std::array<int, 3> arr{1, 2, 3};
locate(arr, 2);

{% endhighlight %}

`T` is deduced to be of type `int`, and `size` is deduced to have value `3`. So again
the deduction works as expected. Note, however, that the types must be exactly the
same. It is not sufficient for the types to simply be convertable to one another. So
`locate(arr, 'c')` will fail to compile, even though `char` is convertable to `int`,
because the compiler cannot deduce a consistent type for `T`.

---

### What about Classes?

You might now be thinking to yourself, "Wow, that's great! So can I use this with
everything?" The answer is, unfortunately, not quite. Classes cannot deduce their
parameter types from the types of their constructor arguments (or indeed from any
member function arguments). So this

{% highlight c++ %}

template<typename T>
struct Foo {
    Foo(T t){...}
};

void main() {
    Foo f{10}; //T is deduced to be int
}

{% endhighlight %}

will not work. It is easy to see reasons why it would be problematic. For example,
if this were true, it could lead to some very confusing results. 

{% highlight c++ %}

template<typename T>
struct Foo {
    Foo(T t){...}
    Foo<T> operator=(const Foo<T>& f){...}
};

void main() {
    Foo f1{10};
    Foo f2{1.0};
    f1 = f2 //fails to compile
}

{% endhighlight %}

The above fails to compile because `f1` would be deduced to have type `Foo<int>`
while `f2` would be deduced to have type `Foo<double>`. As these are fundamentally
distinct types, there is no conversion from `Foo<double>` to `Foo<int>`, and so
there is no way to call `f1`'s `operator=` with `f2`.

_One should note, that there are other good arguments against this behavior arising
from the usage of template class specialization which are beyond the scope of this
post._

All hope is not lost, however. If functions can preform template argument deduction,
we can simply use a function to create an instance of our class. Returning to the
earlier example, let's suppose we want to deduce an appropriate `T` using only
the type of an argument. This may be easily achieved by creating a free function.

{% highlight c++ %}

template<typename T>
Foo make_foo(const T& t) {
    return Foo<T>{t};
}
...
auto f = make_foo(10); // f has type Foo<int>

{% endhighlight %}

At first glance this may appear to be longer than specifying the type manually.
Leaving aside the possibility of human error, it is often the case that the
type would be cumbersome to write by hand. I certainly wouldn't want to have to write
`std::vector<std::pair<int, float>>` all over the place (yes creating an alias would
mitigate this problem somewhat, but why make one if you don't need to).

The astute reader may notice a familiarity with this pattern already. The STL makes
use of it at several points with `make_pair`, `make_shared` and others.

---

###Remote Argument Deduction

There is a notable hole in the "always use template argument deduction" proposal.
Namely, the following will not compile:

{% highlight c++ %}

template<typename funcType, typename argType>
void callFunc(funcType f, argType arg) {
    f(arg);
}

template<typename T>
void func(T t){...}
...
callFunc(func, 10); //compiler error

{% endhighlight %}

This fails because `func` in the last line is a shorthand for `&func`, and it is
not possible (or meaningful) to take the address of a template function, only of its
specializations. So, the following will work `callFunc(func<int>,10)`, but we have
again reverted to explicitly writing the template parameters.

But fear not, this problem is not insurmountable.  While we were saved before by
using a function to create class instances, perhaps now classes will return the
favor. Suppose we have the following class:

{% highlight c++ %}

struct Func {
    template<typename T>
    void operator()(T t) {
        func(t);
    }
};

{% endhighlight %}

We use the class's `operator()` as a template function, but we can create and pass
an instance of Func simply by calling `callFunc(Func{}, 10)`. A very similar approach
to the above appears in the C++14 augmentation of `std::less` and `std::greater`
available [here][paper] authored by the great Stephan T. Lavavej.

[paper]: http://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3421.htm

###What else?

Using the tools above should allow the reader to exploit template argument deduction
in most common circumstances. The complete rules of TAD may, of course be found in
14.8.2 of the latest working draft of the standard available [here][isocpp].

[isocpp]: http://www.isocpp.org

Additionally, I highly recommend Stephan Lavavej's 'Going Native 2013' video on
not helping the compiler in general, available [here][channel9].

[channel9]: http://channel9.msdn.com/Events/GoingNative/2013/Don-t-Help-the-Compiler
