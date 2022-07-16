Title: Exploring Dynamic Dispatch in Rust
Date: 2017-03-07
Slug: exploring-dynamic-dispatch-in-rust
Tags: rust

Let me preface this by saying that I am a novice in the world of rust (though I'm liking things so far!), so if I make technical mistakes please let me know and I will try to correct them. With that out of the way, lets get started.

My real motivation for taking a closer look at dynamic dispatch can be seen in the following code snippet. Suppose I want to create a struct `CloningLab` that contains a vector of trait objects (in this case, `Mammal`):

<script src="https://gist.github.com/ALSchwalm/b43986e11db2d864ee9adf090dedfa45.js"></script>


This works fine. You can iterate over the vector of subjects and call `run` or `walk` as you would expect. However, things break down when you try to add an additional trait to the trait object bounds like:

<script src="https://gist.github.com/ALSchwalm/d56ccd574a3b517ad20a7c6e5dc3f3f8.js"></script>

This fails with the the following error:

    error[E0225]: only the builtin traits can be used as closure or object bounds
     --> test1.rs:3:32
      |
    3 |     subjects: Vec<Box<Mammal + Clone>>,
      |                                ^^^^^ non-builtin trait used as bounds

And I found this surprising. In my mind, a trait object with multiple bounds would be analogous to multiple inheritance in C++. I would expect the object to have multiple vpointers for each 'base', and do dispatch through the appropriate one. Given that rust is still a somewhat young language, I could appreciate why the developers might not want to introduce that complexity immediately (being stuck with a poor design forever would be a high cost for little reward), but I wanted to work out exactly how such a system might work (or not work).

##### Vtables in Rust

Like C++, dynamic dispatch is achieved in Rust  though a table of function pointers (described [here](https://doc.rust-lang.org/1.30.0/book/first-edition/trait-objects.html#representation) in the rust docs). According to that documentation, the memory layout of a `Mammal` trait object made from a `Cat` will consist of two pointers arranged like:

![](/blog/static/images/2017/03/cat_layout-2.png)

I was surprised to see that the data members of the object had an additional layer of indirection. This is unlike the (typical) C++ representation which would look this:

![](/blog/static/images/2017/03/cat_layout_cpp.png)

With the vtable pointer first and the data members immediately following. The rust approach is interesting. It incurs a cost when 'constructing' a trait object, unlike the C++ approach in which a cast to a base pointer is free (or just some addition for multiple inheritance). But this cost is very minor. The rust approach has the benefit that an object does not have to store the vtable pointer if it is never used in a polymorphic context. I think it is fair to say that rust encourages the use of monomorphism, so this is probably a good trade-off.

#####Trait Objects with Multiple Bounds

Returning to the original problem, lets consider how it is resolved in C++. If we have multiple traits (purely abstract classes) that we implement for some structure, then an instance of that structure will have the following layout (e.x., Mammal and Clone):

![](/blog/static/images/2017/03/cat_and_clone_cpp-1.png)

Notice that we now have multiple vtable pointers, one for each base class `Cat` inherits from (that contains virtual functions). To convert a `Cat*` to a `Mammal*`, we don't need to do anything, but to convert a `Cat*` to a `Clone*`, the compiler will add 8 bytes (assuming `sizeof(void*) == 8`) to the `this` pointer.

It is easy to imagine a similar thing for rust:

![](/blog/static/images/2017/03/cat_clone_rust_candidate_1-1.png)

So there are now two vtable pointers in the trait object. If the compiler needs to perform dynamic dispatch on a `Mammal + Clone` trait object, it can access the appropriate entry in the appropriate vtable and perform the call. Because rust does not (yet) support struct inheritance, the problem of determining the correct subobject to pass as `self`, does not exist. `self` will always be whatever is pointed at by the `data` pointer.

This seems like it would work well, but this approach also has some redundancy. We have multiple copies of the type's size, alignment, and `drop` pointer. We can eliminate this redundancy by combining the vtables. This is essentially what happens when you perform trait inheritance like:

<script src="https://gist.github.com/ALSchwalm/b86e7753e26b57776bb00ef46aac6784.js"></script>

Using trait inheritance in this way is a commonly suggested trick to get around the normal limitation of trait objects. The use of trait inheritance produces a single vtable without any redundancy. So the memory layout looks like:

![](/blog/static/images/2017/03/clone_mammal_rust-1.png)

Much simpler! And you can currently do this! Perhaps what we really want is for the compiler to generate a trait like this for us when we try to make a trait object with multiple bounds. But hold on, there are some significant limitations. Namely, you cannot convert a trait object of `CloneMammal` in to a trait object of `Clone`. This seems like very strange behavior, but it is not hard to see why such a conversion won't work.

Suppose you attempt to write something like:

<script src="https://gist.github.com/ALSchwalm/a1acc010590aac091a4d0c968f6024a2.js"></script>

Line 10 must fail to compile because the compiler cannot possibly find the appropriate vtable to put in the trait object. It only knows that the object being referenced implements `CloneMammal`, but it doesn't know which one. Of course, we can tell that it must be a `Cat`, but what if the code was something like:

<script src="https://gist.github.com/ALSchwalm/fc532dbdae257a03c070d02f7e2b9be1.js"></script>

The problem is more clear here. How can the compiler know what vtable to put in the trait object being constructed on line 17? If `clone_mammal` refers to a `Cat`, then it should be the `Cat` vtable for `Clone`. If it refers to a `Dog` then it should be the `Dog` vtable for `Clone`.

So the trait-inheritance approach has this limitation. You cannot convert a trait object in to any other kind of trait object, even when the trait object you want is _more specific_ than the one you already have.

The multiple vtable pointer approach seems like a good way forward to allowing trait objects with multiple bounds. It is trivial to convert to a less-bounded trait object with that setup. The vtable the compiler should use is simply whatever is already `Clone` vtable pointer slot (the second pointer in diagram 4).

##### Conclusions

I hope going through this was a useful exercise to some readers. It certainly helped me organize how I was thinking about trait objects. In practice, I think this is not really a pressing issue, the restriction was just surprising to me.
