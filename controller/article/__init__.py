from . import api, view

views = [
    view.ListArticleHandler, view.EditArticleHandler, view.ViewArticleHandler
]

handlers = [
    api.SaveArticleApi, api.DeleteArticleApi, api.UploadImageApi,
]
