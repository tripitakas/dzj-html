from . import api, view

views = [
    view.TextProofHandler, view.TextReviewHandler, view.TextHardHandler, view.TextEditHandler,
    view.TextSampleProofHandler, view.TextSampleSelectHandler,
]

handlers = [
    api.GetCompareTextApi, api.GetCompareNeighborApi,
    api.TextProofApi, api.TextReviewApi, api.TextHardApi, api.TextEditApi,
]

modules = {'TextArea': view.TextArea}
