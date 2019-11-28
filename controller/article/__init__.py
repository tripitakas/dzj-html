from . import api, view

views = [
    view.EditArticleHandler, view.ViewArticleHandler, view.HelpHandler,
]

handlers = [
    api.SaveArticleApi, api.UploadImageHandler,
]
