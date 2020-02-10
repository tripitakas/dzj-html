// 显隐所有框
$('#toggle-boxes').click(function () {
  var active = !$('#toggle-chars').hasClass('active');
  $('#toggle-blocks').toggleClass('active', active);
  $('#toggle-columns').toggleClass('active', active);
  $('#toggle-chars').toggleClass('active', active);
  $.cut.toggleBox(active, 'block');
  $.cut.toggleBox(active, 'column');
  $.cut.toggleBox(active, 'char');
});

// 显隐栏框
$('#toggle-blocks').click(function () {
  $(this).toggleClass('active');
  $('rect.block').css('display', $(this).hasClass('active') ? 'block' : 'none');
});

// 显隐列框
$('#toggle-columns').click(function () {
  $(this).toggleClass('active');
  $('rect.column').css('display', $(this).hasClass('active') ? 'block' : 'none');
});

// 显隐字框
$('#toggle-chars').click(function () {
  $(this).toggleClass('active');
  $('rect.char').css('display', $(this).hasClass('active') ? 'block' : 'none');
});

// 显隐字序
$('#toggle-chars-no').click(function () {
  $(this).toggleClass('active');
  $.cut.toggleLabel();
});
