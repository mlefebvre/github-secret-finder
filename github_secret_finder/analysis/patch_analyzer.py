from detect_secrets.core.constants import VerifiedResult
from detect_secrets.core.usage import PluginOptions
from detect_secrets.plugins.common import initialize
from unidiff import PatchSet, UnidiffParseError

from .blacklist_matcher import BlacklistMatcher
from .Secret import Secret


class PatchAnalyzer(object):
    def __init__(self, blacklist_file):
        active_plugins = {}
        for plugin in PluginOptions.all_plugins:
            related_args = {}
            for related_arg_tuple in plugin.related_args:
                flag_name, default_value = related_arg_tuple
                related_args[flag_name[2:].replace("-", "_")] = default_value

            active_plugins[plugin.classname] = related_args

        self._plugins = initialize.from_parser_builder(
            active_plugins,
            exclude_lines_regex=None,
            automaton=False,
            should_verify_secrets=True)

        self._blacklist = BlacklistMatcher(blacklist_file)

    def find_secrets(self, patch_text):
        try:
            patch = PatchSet.from_string(patch_text)
        except UnidiffParseError:
            raise StopIteration

        for p in self._plugins:
            for patch_file in patch:
                for chunk in patch_file:
                    for line in chunk.target_lines():
                        if line.is_added:
                            l = line.value.strip()
                            for k in p.analyze_string(l, line.target_line_no, patch_file.path):
                                if self._blacklist.is_blacklisted(l, k.filename, k.secret_value):
                                    continue

                                yield Secret(k.type, k.filename, k.lineno, k.secret_value, p.verify(k.secret_value, content=l) == VerifiedResult.VERIFIED_TRUE)