'use strict';

const products = [
  {id:'coat',name:'Пальто прямого кроя',color:'Песочный',alt:'Бежевое пальто прямого кроя с широкими лацканами',description:'Чёткий силуэт и спокойный оттенок. Завершающий слой для повседневных сочетаний.'},
  {id:'shirt',name:'Классическая рубашка',color:'Белый',alt:'Белая рубашка с длинными рукавами и классическим воротником',description:'Простая форма, которая оставляет место вашему стилю. Самостоятельно или в многослойном образе.'},
  {id:'sweater',name:'Свитер с круглым вырезом',color:'Светло-серый',alt:'Светло-серый свитер с круглым вырезом и длинными рукавами',description:'Лаконичный силуэт без лишних деталей. Для прохладного утра и неспешного вечера.'},
  {id:'trousers',name:'Брюки со стрелками',color:'Чёрный',alt:'Чёрные классические брюки со стрелками',description:'Собранный образ без лишних усилий. Одинаково легко сочетаются с рубашкой и трикотажем.'},
  {id:'dress',name:'Платье без рукавов',color:'Чёрный',alt:'Чёрное платье без рукавов с круглым вырезом',description:'Одна вещь — законченный образ. Чистые линии и детали, которые не требуют дополнений.'},
  {id:'jacket',name:'Укороченная куртка',color:'Оливковый',alt:'Оливковая укороченная двубортная куртка с широким воротником',description:'Знакомая классика в новом силуэте. Сдержанный цвет для повседневного гардероба.'}
];

const grid = document.querySelector('#product-grid');
const dialog = document.querySelector('#product-dialog');
const dialogImage = document.querySelector('#dialog-image');
const closeButton = dialog.querySelector('.close-button');
let lastTrigger = null;

function handleImageError(event) {
  const image = event.currentTarget;
  image.hidden = true;
  image.parentElement.querySelector('.image-fallback').hidden = false;
}

function openProduct(product, trigger) {
  lastTrigger = trigger;
  dialog.querySelector('#dialog-title').textContent = product.name;
  dialog.querySelector('#dialog-color').textContent = product.color;
  dialog.querySelector('#dialog-description').textContent = product.description;
  dialogImage.hidden = false;
  dialogImage.parentElement.querySelector('.image-fallback').hidden = true;
  dialogImage.alt = product.alt;
  dialogImage.src = `assets/${product.id}.jpg`;
  dialog.showModal();
  dialog.scrollTop = 0;
  document.body.classList.add('dialog-open');
}

products.forEach((product, index) => {
  const card = document.createElement('article');
  card.className = 'product-card';
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'product-button';
  button.setAttribute('aria-haspopup','dialog');
  button.setAttribute('aria-label',`Посмотреть: ${product.name}`);
  const picture = document.createElement('div');
  picture.className = 'product-image';
  const image = document.createElement('img');
  image.width = 800;
  image.height = 1000;
  image.alt = product.alt;
  image.loading = index < 3 ? 'eager' : 'lazy';
  image.decoding = 'async';
  if (index === 0) image.fetchPriority = 'high';
  image.addEventListener('error',handleImageError);
  image.src = `assets/${product.id}.jpg`;
  const fallback = document.createElement('span');
  fallback.className = 'image-fallback';
  fallback.textContent = 'Фото пока недоступно';
  fallback.hidden = true;
  const plus = document.createElement('span');
  plus.className = 'product-plus';
  plus.setAttribute('aria-hidden','true');
  plus.innerHTML = '<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>';
  picture.append(image,fallback,plus);
  const info = document.createElement('div');
  info.className = 'product-info';
  const name = document.createElement('h3');
  name.textContent = product.name;
  const color = document.createElement('p');
  color.textContent = product.color;
  info.append(name,color);
  button.append(picture,info);
  button.addEventListener('click',() => openProduct(product,button));
  card.append(button);
  grid.append(card);
});

dialogImage.addEventListener('error',handleImageError);
closeButton.addEventListener('click',() => dialog.close());
dialog.addEventListener('click',(event) => {
  if (event.target !== dialog) return;
  const bounds = dialog.getBoundingClientRect();
  if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
});
dialog.addEventListener('close',() => {
  document.body.classList.remove('dialog-open');
  lastTrigger?.focus({preventScroll:true});
});
