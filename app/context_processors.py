"""Context processors for the app."""

from yt_navigator import __version__


def version_context(request):
    """Add version information to the template context.

    Args:
        request: The HTTP request object

    Returns:
        dict: A dictionary containing the application version
    """
    return {"app_version": __version__}
