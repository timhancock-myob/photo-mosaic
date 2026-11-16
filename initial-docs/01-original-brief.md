Lets do some research

I want to build a photo mosaic application.  This application
1. (base) ask a user to pick a photo - this is the photo which will form the base of the mosaic
2. (tiles) ask a user to input a connection to either google photos or a private folder, with probably hundreds of other photos within it - these are the tile photos that are used to build up the mosaic
3. it will then determine a consistent grid over the base e.g. 20x20, 50x50, that forms the grain of the mosaic over the base
4. then for each cell within the grid it will search to find which tile photo fits better.  this is determined by the general color profile of the photo, especially around the edges.

This is the core application.  It needs a simple gui.

The optional extras will be
1. allows the photos to be rescaled or croped
2. allowing a user to swap out titles and suggest other alternatives
3. ensuring no photo is used twice.

I want you to write a system description for this.  It should be built with python and pythons scientific libraries as the base.  It should use react as the front end.  It has a separable API layer in the middle built with fast API.  Connections to 3rd parties should also be done with an API layer (if requried).

I don't want code yet - i just want a description.
