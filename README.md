# DPMI Visualizer

Visualize data from DPMI consumers.

## Usage

    python -m visualizer -f CONFIG

The "visualizer" module must either be

* installed system-wide in site-packages
* in a path present in PYTHONPATH
* in the current working directory (e.g. cd to the root of this project)

Use `python -m visualizer -h` for general help and `-H PLUGIN` for help
regarding specific plugin.

## Plugins

Plugins take output from a consumer (either in a generic format (e.g. comma-separated values) or a specific format) and renders it onto the screen. It ships with a few simple plugins like `table`, `graph` and `histogram`. 

## Configuration

The visualizer loads a single configuration file (ini-style).

Stub configuration:

    [general]

    [consumer/INDEX]

    [process/INDEX]

    [plugin:PLUGIN/INDEX]
    attribute = value

Each section (with the exception of `general` and `transition`) creates a new item, e.g. "[plugin:foo/0]" creates a new plugin of type foo. The `/0` at the end is the index of this plugin which is only used to separate different instances of the same plugin.

## Consumers and generators

Consumers from DPMI reads packet traces, analyzes the data and generates some form of output. From the visualizers point of view a consumer is an input source (similarly plugins is considered output sinks). Each consumer is given a datasource name which is just used to bind data together. A consumer which generates bitrate data can be given the datasource name "br10" and a plugin can be configured to accept data from the datasource with that name.

A generator is a stub consumer, mostly just generating random data for testing purposes but it can also give a prerecorded set of data.

### Writing plugins

Each plugin is its own file and must contain a few objects:

    name = 'My plugin'
    author = ('My name', 'email@example.net')
    date = '2014-01-12'
    version = 0
    api = 1

    def factory(): pass

The first two fields is for external identification only. The `date` and `version` variables should be bumped upon changes but neither is used internally by the visualizer but rather used when debugging. Next the `api` variable defines what API this plugin uses. Currently there is only a single API present, namely version 1. Future versions may define other APIs. Lastly the `factory` object is called when an instance of the plugin is required. You can either pass a class object `factory = MyPlugin` or write a custom function.

There is two flavors of plugins: [Cairo](http://cairographics.org/) or pure OpenGL. Cairo plugins is best suited when vector graphics is required but is slower to render compared to hardware accelerated OpenGL. See `plugins/sample_cairo.py` and `plugins/sample_opengl.py` respectively. Cairo sample contains extended documentation and is more suitable for starters.

The object returned from the `factory` callable also has some requirements but as long as you create a class inheriting from either `PluginCairo` or `PluginOpenGL` everything is covered. It would be possible to write plugins in c given that the object fulfills the API defined in `PluginBase` (but does not necessarily have to inherit from it).

Plugins does not render directly to the window but is rather confined to a framebuffer which is later drawn. This has two major advantages, first you don't need to keep track of where onto the window you should render: (1,1) is always the upper left corner of your confined area. Secondly, there is no way different plugins interferes with each other, even if you "clear the screen" you won't draw anything onto something else.

## Internal

TBD
