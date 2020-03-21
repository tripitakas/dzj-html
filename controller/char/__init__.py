from . import api, view

views = [
    view.CharBrowseHandler,
]

handlers = [
    api.CharGenImgApi, api.CharUpdateApi, api.PublishCharTasksApi, api.UpdateCharBatchApi,
]
