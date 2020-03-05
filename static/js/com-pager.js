/*
 * com-pager.js
 * Date: 2019-08-15
 */

// 分页-跳转第n页
$('.pagers .page-no').on("keydown", function (event) {
  var keyCode = event.keyCode || event.which;
  if (keyCode === 13) {
    var page = $(this).val().trim();
    page = page > 1 ? page : 1;
    location.href = setQueryString('page', page);
  }
});

// 分页-每页显示n条
$('.pagers .page-size').on("change", function () {
  location.href = setQueryString('page_size', this.value);
});