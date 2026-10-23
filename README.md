# Alikz' 3D1 Toolkit

## About

This repository contains a bundle of tools tailored to making aspects of the **3D1** workflow faster, less tedious or less stressful.

> [!NOTE]
> If you encounter any problems or bugs, or want me to add a feature, don't hesitate to contact me on discord or anywhere else really.

## Tools Overview

### **Sanity Checker (CTRL + SHIFT + V)**

When the keybind is pressed anywhere in the **3D View** a pop-up will open.

This pop-up will list all of the following problems:

* **Object Naming**: Any *object* that is missing the 'SM_' prefix. Do not forget to also give your objects proper names.
* **Material Naming**: Any *material* that is missing the 'M_' prefix. Do not forget to also give your materials proper names.
* **N-Gons**: Any *object* that contains n-gons in it's geometry.
* **Non-Manifolds**: Any *object* that contains non-manifolds in it's geometry.
* **Overlapping Geometry**: Any *object* that contains overlapping geometry.
* **Unapplied Modifiers**: Any *object* that has unapplied modifiers attached to it.
* **Unused Materials**: All *materials* that are not being used on any object in the file.
* **Unused Textures**: All *textures* that are not being used in the file.
* **PSD Textures**: All **Photoshop** *textures* still being used in the file. Make sure to replace these with the exported textures.

### **Fast Blueprints (CTRL + SHIFT + B)**

Will let you upload blueprints for all cardinal directions and handles the creation of all planes and materials. All you still have to do is resize the blueprints according to the size of the object you want to make.
