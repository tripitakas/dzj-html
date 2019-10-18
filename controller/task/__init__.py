from . import api, view

views = [
    view.TaskLobbyHandler, view.MyTaskHandler, view.TaskAdminHandler,
]

handlers = [
    api.PickTaskApi, api.ReturnTaskApi, api.UnlockTaskDataApi, api.RetrieveTaskApi,
    api.DeleteTasksApi, api.GetReadyTasksApi, api.PublishTasksApi, api.AssignTasksApi,
    api.FinishTaskApi,
]
