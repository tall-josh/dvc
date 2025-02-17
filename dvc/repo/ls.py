from itertools import chain

from dvc.exceptions import PathMissingError
from dvc.path_info import PathInfo


@staticmethod
def ls(
    url, path=None, rev=None, recursive=None, dvc_only=False,
):
    """Methods for getting files and outputs for the repo.

    Args:
        url (str): the repo url
        path (str, optional): relative path into the repo
        rev (str, optional): SHA commit, branch or tag name
        recursive (bool, optional): recursively walk the repo
        dvc_only (bool, optional): show only DVC-artifacts

    Returns:
        list of `entry`

    Notes:
        `entry` is a dictionary with structure
        {
            "path": str,
            "isout": bool,
            "isdir": bool,
            "isexec": bool,
        }
    """
    from dvc.external_repo import external_repo

    with external_repo(url, rev) as repo:
        path_info = PathInfo(repo.root_dir)
        if path:
            path_info /= path

        ret = _ls(repo, path_info, recursive, dvc_only)

        if path and not ret:
            raise PathMissingError(path, repo, dvc_only=dvc_only)

        ret_list = []
        for path, info in ret.items():
            info["path"] = path
            ret_list.append(info)
        ret_list.sort(key=lambda f: f["path"])
        return ret_list


def _ls(repo, path_info, recursive=None, dvc_only=False):
    from dvc.tree.repo import RepoTree

    def onerror(exc):
        raise exc

    # use our own RepoTree instance instead of repo.repo_tree since we want to
    # fetch directory listings, but don't want to fetch file contents.
    tree = RepoTree(repo, stream=True)

    infos = []
    try:
        for root, dirs, files in tree.walk(
            path_info.fspath, onerror=onerror, dvcfiles=True
        ):
            entries = chain(files, dirs) if not recursive else files
            infos.extend(PathInfo(root) / entry for entry in entries)
            if not recursive:
                break
    except NotADirectoryError:
        infos.append(path_info)
    except FileNotFoundError:
        return {}

    ret = {}
    for info in infos:
        metadata = tree.metadata(info)
        if metadata.output_exists or not dvc_only:
            path = (
                path_info.name
                if path_info == info
                else str(info.relative_to(path_info))
            )
            ret[path] = {
                "isout": metadata.is_output,
                "isdir": metadata.isdir,
                "isexec": metadata.is_exec,
            }
    return ret
