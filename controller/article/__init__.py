from . import api, view

views = [
    view.ArticleListHandler, view.ArticleAddOrUpdateHandler, view.ArticleViewHandler
]

handlers = [
    api.ArticleAddOrUpdateApi, api.ArticleDeleteApi, api.UploadImageApi,
]
