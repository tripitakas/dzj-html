from . import api, view

views = [
    view.TextProofHandler, view.TextReviewHandler, view.TextHardHandler,
]

handlers = [
    api.SaveTextProofApi, api.SaveTextReviewApi, api.SaveTextHardApi,
    api.GetCompareTextApi, api.GetCompareNeighborApi,
]

modules = {'TextArea': view.TextArea}

