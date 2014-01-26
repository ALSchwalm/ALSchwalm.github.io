---
layout: post
title: A Careful Introduction to enable_if
categories:
- blog
tags: [C++, templates]
---

It is impossible to discuss the utility of `enable_if` without first discussing,
at least in brief, overload resolution and SFINAE. Without delving too deeply into
these topics, below is a quick introduction.

###Overload Resolution and SFINAE

Whether one loves or hates it, every C++ programmer is familiar with overloading
functions. The compiler's ability to choose an appropriate function based on
arguments passed is integral to many C++ APIs. However, this is also a feature for
which the language is often criticized. Developers from languages without such a
feature often complain about the difficulty in determining which function will
actually be called when overload resolution is finished. These difficulties are, in
my opinion somewhat overstated, and it is difficult for me to see that having `abs`,
`labs`, and `llabs` (for finding the absolute value of an `int`, `long`, and
`long long` respectively in C) is somehow superior to one overloaded function.

That is not to say there is no complexity in overload resolution. There certainly is,
but the cleverness of the process is that most developers need not know the rules
in their entirety (or really at all) in order to exploit the power of the feature.
How often is it that the compiler chooses the incorrect overload? The rules laid out
in the standard are remarkably good at choosing the function the developer intended
to call.

The process of calling a function may be thought of as being divided into the
following rough phases (note that this is a simplification, there are other phases
such as access control which are not mentioned here at all):

1.  Name Lookup
2.  Template Argument Deduction
3.  Overload Resolution

The first of these phases finds all names in the available scopes which match the
name of the called function. The rules involving which scopes will be examined are
not particularly relevant to the discussion at hand, and so will be ignored.

Template Argument Deduction (discussed somewhat [here][TAD]) attempts to specialize
a given template function to create something matching the arguments passed
to the function.

[TAD]: /blog/2014/01/23/Template-argument-deduction-CPP.html

After these first two phases complete, the compiler is effectively left with a set
of viable function (known as the overload set) from which the compiler chooses a
'winner', or declares an ambiguity. Again the exact rules by which the winner is
chosen are beyond the scope of this post. The important thing to note is that this
set contains only _viable_ functions. 

If, for example, I had two functions declared:

{% highlight c++ %}

template<typename T>
void func(typename T::type t){...}

void func(int i){...}

{% endhighlight %}

And I called `func(10)`, one might expect that this would be a compile time error.
After all, `int` clearly has no internal typedef `type`, so the first signature is
nonsensical (and so nonviable). This would make it very difficult to use template
functions in overload resolution, however. C++, thankfully, solves this problem with
a rule known as SFINAE, or "Substitution Failure Is Not An Error". As its name
implies, this rule states that when a type cannot be meaningfully substituted (either
manually or by template argument deduction) this does not constitute a compile time
error. Instead, the offending function is simply removed from the overload set and
not considered. The end result of this is that the above function call invokes the
second function, just as the programmer probably intended.

It is important to note that it is only the signature of the function which is
relevant to the above proceedings. If SFINAE applied to the definitions of the
functions, it would result in the terrible behavior that, if a bug is introduced to
an overloaded template function, the compiler may silently remove that function from
the overload set rather than throwing an error. For example:

{% highlight c++ %}

template<typename T>
T increment(T t){return t+10;} //general function

template<>
int increment<int>(int i) {   //explicit specialization on 'int'
    return i++20;  //typo
}

{% endhighlight %}

If I called `increment(10)`, I would certainly expect to get back 30. However, if
SFINAE applied to the definition of the function as well as the signatures, the
above bug would force the compiler to remove the explicit specialization from the
overload set, leaving only the `increment<int>` created by the compiler (i.e.,
`int increment(int t){return t+10;}`). This behavior would create an extremely
subtle category of bugs. Without it, the programmer may be confident that changing
the body of a function cannot possibly change which function is selected by the
process of overload resolution.

_Note that this is similar to the reason that access control is applied so late in
the process of calling a function. If moving a function from private to public
resulted in the compiler silently choosing a different function, it would also create
a very subtle category of bugs._

###Enter: enable_if

`enable_if` acts as a way to remove things from the overload set manually. It is sometimes
necessary to create overloaded behavior on things not as cleanly divisible as `int`
or `float`. If, for example, a programmer wished for a function to have a distinct
behavior based upon whether an argument was any of the integral types  (i.e., `int`,
`long`, etc.) or floating point (`float`, `double`, etc.), it would be cumbersome to
achieve using only basic overloads. The developer may have to create functions for
each of the possible integral or floating point types, each containing lots of
redundant code.

Clearly this solution is non-optimal. `enable_if` exploits SFINAE to create non-viable
functions under chosen conditions, and so remove those functions from the overload
set. The above problem can be solved with SFINAE as follows

{% highlight c++ %}

template<typename T>
typename enable_if<is_integral<T>::value>::type
foo(T t){...}

template<typename T>
typename enable_if<is_floating_point<T>::value>::type
foo(T t){...}

{% endhighlight %}

The first function will be called for any case where `T` is of integral type, and
the second will be called when `T` is of floating point type. Clearly this is not the
simplest syntax in the world, especially if this is your first time seeing anything
like this. Allow me to elucidate.

`is_floating_piont<T>::value` is simple enough. It is a struct with a static member
`value` which will be `true` when `T` is floating point, and `false` when it is not.
`enable_if` is somewhat trickier. Its declaration is:

{% highlight c++ %}

template< bool B, class T = void >
struct enable_if;

{% endhighlight %}

The struct has a typedef `type` of type `T` when `B` is `true`, and has no internal
typedef when `B` is false. This is important because, in the example above when,
say, `is_integral<T>::value` is false, the function will have no return type. It will
be removed from the overload set leaving only the desired function.

###Using it with classes

The above discussion has focused on functions, but `enable_if` may be used to create
a similar effect in classes. Take, for example the following class declarations

{% highlight c++ %}

template<typename T, typename Enable = void>
struct Foo; //undefined case for types which are neither integral nor floating point

template<typename T>
class Foo<T, typename enable_if<is_integral<T>::value>::type>{...};

template<typename T>
class Foo<T, typename enable_if<is_floating_point<T>::value>::type>{...};

{% endhighlight %}

Again the syntax is not the most concise. It is not impenetrable, however. The key to
this usage is the `Enable` parameter. Referring to the above signature of `enable_if`,
notice that the default type is `void`. We default `Enable` to `void`, so that if
`enable_if`'s `B` is `true`, its internal typedef "`type`", will match `Enable` and
that specialization will be selected.

The end result of this is that if I create an instance of type `Foo<int>` the first
specialization will be selected, and if I create and instance of type `Foo<float>`,
the second will be selected.

###Don't use enable_if

The principle difficulty in using `enable_if` is not understanding how it functions,
but in resisting the urge to use it. There are, in fact, relatively few cases in
which the above behavior is necessary, and even when it is desirable, it is typically
better achieved using other methods.

One of these alternatives is a technique known as "tag dispatch". The idea here is
to have one general function, and then call helper functions to perform the actual
work. The behavior of the above functions could be achieved as follows:

{% highlight c++ %}

namespace helpers {
    template<typename T> //called for integral types
    void foo(T t, std::true_type){...}

    template<typename T> //called for floating point types
    void foo(T t, std::false_type){...}
}

template<typename T>
void foo(T t) {
    helpers::foo(t, typename is_integral<T>::type{});
}

{% endhighlight %}

In this sample, the helper functions have an additional argument of either `true_type`
or `false_type`. These are types analogous to the values `true` and `false`, which
allow the compiler to determine which overload to call. `is_integral<T>::type` is
a type which inherits from either `true_type` or `false_type`, so we create an
instance of the given type and pass it as the second argument. These types are
completely distinct, leaving only one possible function to call.

A principle advantage of taking the above approach over `enable_if` is that the API
is significantly cleaner. Take `template<typename T> void foo(T t)` verses
`template<typename T> typename enable_if<is_integral<T>::value>::type foo(T t)`.

The latter approach also reduces the risk of ambiguous calls arising from types
satisfying the condition for multiple `enable_if`s. If, for example, a type was
somehow able to be _both_ integral and floating point (an impossibility, but a
situation certainly possible with other combinations of conditions), the
`enable_if` approach would create an ambiguous call, as both functions would be
in the overload set. The second approach is always unambiguous, as a type must be
either integral or not integral. 
