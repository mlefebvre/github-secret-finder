from datetime import datetime, timedelta


class GithubBranch(object):
    def __init__(self, name, sha):
        self.sha = sha
        self.name = name

    def get_commits_url(self, repo: 'GithubRepository', since: datetime = None):
        url = "https://api.github.com/repos/%s/commits?sha=%s" % (repo.name, self.sha)
        if since is not None:
            url += "&since=" + since.strftime("%Y-%m-%dT%H:%M:%SZ")
        return url

    @staticmethod
    def from_json(json) -> 'GithubBranch':
        return GithubBranch(json["name"], json["commit"]["sha"])


class GithubRepository(object):
    def __init__(self, name: str, default_branch: str, is_fork: bool, parent: 'GithubRepository'):
        self.name = name
        self.default_branch = default_branch
        self.parent = parent
        self.is_fork = is_fork

    def get_branches_url(self):
        return "https://api.github.com/repos/%s/branches" % self.name

    def get_contributors_url(self):
        return "https://api.github.com/repos/%s/contributors" % self.name

    def get_compare_url(self, base: GithubBranch, head: GithubBranch, compare_with_parent=False):
        if compare_with_parent:
            return "https://api.github.com/repos/%s/compare/%s...%s:%s" % (self.parent.name, base.name, self.name.split("/")[0], head.name)
        else:
            return "https://api.github.com/repos/%s/compare/%s...%s" % (self.name, base.name, head.name)

    @staticmethod
    def from_json(json) -> 'GithubRepository':
        parent = None
        if "parent" in json:
            parent = GithubRepository.from_json(json["parent"])
        return GithubRepository(json["full_name"], json["default_branch"], json["fork"], parent)


class BaseGithubCommit(object):
    def __init__(self, sha, api_url, date: datetime):
        self.date = date
        self.api_url = api_url
        self.sha = sha

    @staticmethod
    def _parse_date(s):
        try:
            if len(s) >= 25:
                return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S") + (1 if s[19] == '-' else -1) * timedelta(
                    hours=int(s[20:22]), minutes=int(s[23:25]))
            else:
                return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            return datetime.min


class GithubCommit(BaseGithubCommit):
    def __init__(self, sha, api_url, html_url, date: datetime):
        super().__init__(sha, api_url, date)
        self.html_url = html_url

    def __str__(self):
        return "%s (%s)" % (self.sha, self.date)

    @staticmethod
    def from_json(json) -> 'GithubCommit':
        return GithubCommit(json["sha"], json["url"], json["html_url"], BaseGithubCommit._parse_date(json["commit"]["committer"]["date"]))


class GithubUser(object):
    def __init__(self, login, name, email):
        self.login = login.lower() if login else None
        self.name = name.lower() if name else None
        self.email = email.lower() if email else None

    def __hash__(self):
        return hash((self.login, self.email, self.name))

    def __eq__(self, other):
        return (self.login, self.email, self.name) == (other.login, other.email, other.name)

    @staticmethod
    def from_user_json(json) -> 'GithubUser':
        return GithubUser(json["login"], json["name"], json["email"])

    @staticmethod
    def from_commit_json(json, user_type) -> 'GithubUser':
        commit_user = json["commit"][user_type]
        login = None
        if json[user_type] is not None:
            login = json[user_type]["login"]
        return GithubUser(login, commit_user["name"], commit_user["email"])


class GithubCommitWithUsers(BaseGithubCommit):
    def __init__(self, sha, api_url, date: datetime, committer: GithubUser, author: GithubUser):
        super().__init__(sha, api_url, date)
        self.author = author
        self.committer = committer

    @staticmethod
    def from_json(json) -> 'GithubCommitWithUsers':
        commit = json["commit"]
        author = GithubUser.from_commit_json(json, "author")
        committer = GithubUser.from_commit_json(json, "committer")
        return GithubCommitWithUsers(json["sha"], json["url"], BaseGithubCommit._parse_date(commit["committer"]["date"]), committer, author)
