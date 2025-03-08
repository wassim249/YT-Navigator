from django.shortcuts import render


def page_not_found(request, exception):
    """
    404 error handler
    """
    return render(request, "errors/404.html", status=404)


def server_error(request):
    """
    500 error handler
    """
    return render(request, "errors/500.html", status=500)
