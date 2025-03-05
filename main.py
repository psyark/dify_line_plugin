""" このモジュールではプラグインを実行します """
from dify_plugin import Plugin, DifyPluginEnv  # type: ignore

plugin = Plugin(DifyPluginEnv(MAX_REQUEST_TIMEOUT=120))

if __name__ == '__main__':
    plugin.run()
