from . import api, view

views = [
    view.EditArticleHandler, view.ViewArticleHandler,
]

handlers = [
    api.SaveArticleApi, api.UploadImageHandler,
]
