from . import api, view

views = [
    view.ArticleAdminHandler, view.ArticleUpsertHandler, view.ArticleViewHandler,
    view.ArticleListHandler,
]

handlers = [
    api.ArticleUpsertApi, api.ArticleDeleteApi, api.UploadImageApi,
]
