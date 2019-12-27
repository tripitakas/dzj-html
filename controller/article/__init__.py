from . import api, view

views = [
    view.ArticleAdminHandler, view.ArticleAddOrUpdateHandler, view.ArticleViewHandler,
    view.ArticleListHandler,
]

handlers = [
    api.ArticleAddOrUpdateApi, api.ArticleDeleteApi, api.UploadImageApi,
]
