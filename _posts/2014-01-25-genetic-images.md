---
layout: project
title: Genetic Images
link: https://github.com/ALSchwalm/GeneticImages
status: Completed
updated: 6/11/2013 
images:
- genetic1.png
- genetic2.png
- genetic3.png
image-title: Images created by the program
image-gallery: geneticGallery
categories:
- project
tags: C++, genetic
---

This is a python script which uses [pyEvolve(v0.6+)][evolve] to grow images. The
'alleles' in the script are functions of of the X and Y coordinates of a point. The
resultant genome is the tree of those functions. That fuction is then applied to
every point in sequence returning an RGB value for that point.

[evolve]: http://pyevolve.sourceforge.net/0_6rc1/
