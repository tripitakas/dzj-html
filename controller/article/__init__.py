from . import api, view

views = [
    view.ListArticleHandler, view.ArticleAddOrUpdateHandler, view.ArticleViewHandler
]

handlers = [
    api.SaveArticleApi, api.DeleteArticleApi, api.UploadImageApi,
]
