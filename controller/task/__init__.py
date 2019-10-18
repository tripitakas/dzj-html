from . import api, view

views = [
    view.TaskLobbyHandler, view.MyTaskHandler, view.TaskAdminHandler,
]

handlers = [
    api.PickTaskApi, api.ReturnTaskApi, api.GetPageApi, api.UnlockTaskDataApi,
    api.RetrieveTaskApi, api.DeleteTasksApi,
    api.GetReadyTasksApi, api.PublishTasksApi,
]

