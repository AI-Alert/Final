import os

from django.contrib.auth import authenticate, login, logout as django_logout # Use alias like "django_logout" so that django doesnt get confused on which function to use.
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.db.models import Q
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from .models import Member, Product, Image
from .forms import *
from .helpers import Helpers

#Главная страница
def index(request):
	return render(request, Helpers.get_url('index.html'))
#Отдельный продукт
def single_product(request, product_id):
	product = get_object_or_404(Product, pk=product_id)
	product_images = product.image_set.all()
	images = []
	
	if product_images:
		for data in product_images:
			images.append({"small": Helpers.get_path(str(data.image)), 'big': Helpers.get_path(str(data.image))})
	
	return render(request, Helpers.get_url('product/single.html'), {'product': product, 'images': str(images).replace("'", '"')})
	
	# Поля для товара
def products(request):
	if request.method == 'POST':
		pagination_content = ""
		page_number = request.POST['data[page]'] if request.POST['data[page]'] else 1
		page = int(page_number)
		name = request.POST['data[name]']
		sort = '-' if request.POST['data[sort]'] == 'DESC' else ''
		search = request.POST['data[search]']
		max = int(request.POST['data[max]'])
		
		cur_page = page
		page -= 1
		per_page = max 
		start = page * per_page
		
		if search:		 
			all_posts = Product.objects.filter(Q(content__contains = search) | Q(name__contains = search)).exclude(status = 0).order_by(sort + name)[start:per_page]
			count = Product.objects.filter(Q(content__contains = search) | Q(name__contains = search)).exclude(status = 0).count()
			
		else:
			all_posts = Product.objects.exclude(status = 0).order_by(sort + name)[start:cur_page * max]
			count = Product.objects.exclude(status = 0).count()
		
		if all_posts:
			for post in all_posts:
				pagination_content += '''
					<div class='col-sm-3'>
						<div class='panel panel-default'>
							<div class='panel-heading'>%s</div>
							<div class='panel-body p-0 p-b'>
								<a href='%s'>
									<img src='%s' width='%s' class='img-responsive'>
								</a>
								<div class='list-group m-0'>
									<div class='list-group-item b-0 b-t'>
										<i class='fa fa-calendar-o fa-2x pull-left ml-r'></i>
										<p class='list-group-item-text'>Price</p>
										<h4 class='list-group-item-heading'>$%s</h4>
									</div>
									<div class='list-group-item b-0 b-t'>
										<i class='fa fa-calendar fa-2x pull-left ml-r'></i>
										<p class='list-group-item-text'>On Stock</p>
										<h4 class='list-group-item-heading'>%d</h4>
									</div>
								</div>
							</div> 
							<div class='panel-footer'>
								<a href='%s' class='btn btn-primary btn-block'>View Item</a>
							</div>
						</div>
					</div>
				''' %(post.name, Helpers.get_path('product/' + str(post.id)), Helpers.get_path(post.featured_image), '100%', post.price, post.quantity, Helpers.get_path('product/' + str(post.id)))
		else:
			pagination_content += "<p class='bg-danger p-d'>No results</p>"
		
		return JsonResponse({
			'content': pagination_content, 
			'navigation': Helpers.nagivation_list(count, per_page, cur_page)
		})
	else:	
		return render(request, Helpers.get_url('product/index.html'))

#	Вход пользователем
def user_login(request):
	if request.user.is_authenticated:
		return HttpResponseRedirect(Helpers.get_path('user/account'))
	
	if request.method == 'POST':
		username = request.POST['username']
		password = request.POST['password']
		# Валидация username и password
		user = authenticate(username=username, password=password)
		if user is not None:
			# Успешно выполнено 
			login(request, user)
			# Перенаправляет на авторизацию
			return HttpResponseRedirect(Helpers.get_path('user/account'))
		else:
			return render(request, Helpers.get_url('user/login.html'), {'error_message': 'Incorrect username and / or password.'})
	else:
		return render(request, Helpers.get_url('user/login.html'))
 
def user_account(request):
	err_succ = {'status': 0, 'message': 'An unknown error occured'}
	
	# Создание новой формы
	form = AccountForm(request.POST)
	
	# Перенаправляет на регистрацию, если не зарегестрирован
	if request.user.is_authenticated == False:
		return HttpResponseRedirect(Helpers.get_path('user/login')) 
	
	if request.method == 'POST':
		if form.is_valid():	
			# Запрос для добавление залогированного пользователя
			user = User.objects.get(username=request.user.username)
			
			# Проверка никнейма
			if User.objects.filter(username=form.cleaned_data['username']).exists() and user.username != form.cleaned_data['username']:
				err_succ['message'] = 'Username aleady taken, please enter a different one.'
			
			# Проверка почты		
			elif User.objects.filter(email=form.cleaned_data['email']).exists() and user.email != form.cleaned_data['email']:
				err_succ['message'] = 'Email already taken, please enter a different one'
				
			elif form.cleaned_data['old_password'] and form.cleaned_data['password_repeat'] and form.cleaned_data['password']:
				# Проверка на совпадение пароля
				if form.cleaned_data['password_repeat'] != form.cleaned_data['password']:
					err_succ['message'] = 'New password do not match.'
				
				# Проверка на корректность пароля
				elif not user.check_password(form.cleaned_data['old_password']):
					err_succ['message'] = 'Incorrect old password.'
					
			else:
				user.username = form.cleaned_data['username']
				user.first_name = form.cleaned_data['first_name']
				user.last_name = form.cleaned_data['last_name']
				
				user.member.phone_number = form.cleaned_data['phone_number']
				user.member.about = form.cleaned_data['about_me']
				
				# Если прошла валидацию, сохранять пароль
				if form.cleaned_data['password']:
					user.set_password(form.cleaned_data['password'])
				
				# Сохранять поля
				user.member.save()
				user.save()
				
				# Ошибки нет
				err_succ['status'] = 1
				err_succ['message'] = 'Аккаунт успешно обновлен!'
			
		return JsonResponse(err_succ)
	else:
		# Информация о пользователе
		user_data = {
			'username': request.user.username, 
			'email': request.user.email, 
			'first_name': request.user.first_name, 
			'last_name': request.user.last_name, 
			'phone_number': request.user.member.phone_number, 
			'about_me': request.user.member.about 
		}
		# переходит в аккуанты
		return render(request, Helpers.get_url('user/account.html'), {'form': AccountForm(initial=user_data)})

def user_products(request):
	# перенаправляет на регистрацию, если пользователь не авторизован
	if request.user.is_authenticated == False:
		return HttpResponseRedirect(Helpers.get_path('user/login'))
	
	if request.method == 'POST':
		pagination_content = ""
		page_number = request.POST['data[page]'] if request.POST['data[page]'] else 1
		page = int(page_number)
		name = request.POST['data[th_name]']
		sort = '-' if request.POST['data[th_sort]'] == 'DESC' else ''
		search = request.POST['data[search]']
		max = int(request.POST['data[max]'])
		
		cur_page = page
		page -= 1
		per_page = max # Set the number of results to display
		start = page * per_page
		
		# Поиск по базе 
		if search:		 
			all_posts = Product.objects.filter(Q(content__contains = search) | Q(name__contains = search), author = request.user.id).order_by(sort + name)[start:per_page]
			count = Product.objects.filter(Q(content__contains = search) | Q(name__contains = search), author = request.user.id).count()
			
		else:
			all_posts = Product.objects.filter(author = request.user.id).order_by(sort + name)[start:cur_page * max]
			count = Product.objects.filter(author = request.user.id).count()
		
		if all_posts:
			for post in all_posts:
				pagination_content += '''
					<tr>
						<td><a href="%s"><img src='%s' width='100' /></a></td>
						<td>%s</td>
						<td>$%s</td>
						<td>%s</td>
						<td>%s</td>
						<td>%s</td>
						<td>
							<a href='%s' class='text-success'>  
								<span class='glyphicon glyphicon-pencil' title='Edit'></span>
							</a> &nbsp; &nbsp;
							<a href='#' class='text-danger delete-product' item_id='%s'>
								<span class='glyphicon glyphicon-remove' title='Delete'></span>
							</a>
						</td>
					</tr>
				''' %(Helpers.get_path('user/product/update/' + str(post.id)), Helpers.get_path(post.featured_image), post.name, post.price, post.status, post.date, post.quantity, Helpers.get_path('user/product/update/' + str(post.id)),  post.id)
		else:
			pagination_content += "<tr><td colspan='7' class='bg-danger p-d'>No results</td></tr>"
		
		return JsonResponse({
			'content': pagination_content, 
			'navigation': Helpers.nagivation_list(count, per_page, cur_page)
		})
	else:	
		return render(request, Helpers.get_url('product/user.html'))
	
#создание товара

def user_product_create(request):
	err_succ = {'status': 0, 'message': 'An unknown error occured'}
	

	if request.user.is_authenticated == False:
		return HttpResponseRedirect(Helpers.get_path('user/login'))
	

	form = CreateProductForm(request.POST)
	
	if request.method == 'POST':
		if form.is_valid():	
			product = Product.objects.create(
				name = form.cleaned_data['name'],
				content = form.cleaned_data['content'],
				excerpt = form.cleaned_data['excerpt'],
				price = form.cleaned_data['price'],
				status = form.cleaned_data['status'],
				quantity = form.cleaned_data['quantity'],
				author = request.user.id
			)	
			product.save()
			
			err_succ['status'] = 1
			err_succ['message'] = product.id
			
		return JsonResponse(err_succ)
	else:	
		return render(request, Helpers.get_url('product/create.html'), {'form': CreateProductForm()})
	
	#Обновление товара

def user_product_update(request, product_id):
	
	product = get_object_or_404(Product, pk=product_id)
	
	
	err_succ = {'status': 0, 'message': 'An unknown error occured', 'images': []}
		
	if request.user.is_authenticated == False:
		return HttpResponseRedirect(Helpers.get_path('user/login'))
	
	form = UpdateProductForm(request.POST)
	
	if request.method == 'POST':
		if form.is_valid():		
			if product.author != request.user.id:
				err_succ['message'] = 'You are not the author of this product.'
			else:
				# Обновление полей
				product.name = form.cleaned_data['name']
				product.content = form.cleaned_data['content']
				product.excerpt = form.cleaned_data['excerpt']
				product.price = form.cleaned_data['price']
				product.status = form.cleaned_data['status']
				product.quantity = form.cleaned_data['quantity']
				product.save()
				
				# Проверка изображения
				if request.FILES.getlist('images'):	
			
					product_location = 'media/products/' + str(product.id)
					
					# Махинации с фотографией
					for post_file in request.FILES.getlist('images'):
						
						fs = FileSystemStorage(location=product_location)
						
						filename = fs.save(post_file.name, post_file)
					
						uploaded_file_url = product_location + '/' + filename
						
						err_succ['images'].append(uploaded_file_url)
						
						image = Image.objects.create(
							product = product,
							image = uploaded_file_url
						)
						image.save()
				
				# Успешно выполнено
				err_succ['status'] = 1
				err_succ['message'] = 'Продукт обновлен успешно!'
					
		return JsonResponse(err_succ)
	else:
		
		product_data = {
			'name': product.name,
			'content': product.content,
			'excerpt': product.excerpt,
			'price': product.price,
			'status': product.status,
			'quantity': product.quantity,
		}
		return render(request, Helpers.get_url('product/update.html'), {'form': UpdateProductForm(initial=product_data), 'product': product}) # Include product object when rendering the view.

#обновление изображения

def set_featured_image(request):
	
	product = get_object_or_404(Product, pk=request.POST['product_id'])

	err_succ = {'status': 0, 'message': 'An unknown error occured'}
	
	
	if request.user.is_authenticated == False or product.author != request.user.id:
		return JsonResponse(err_succ)
	
	
	if request.method == 'POST':
	
		product.featured_image = request.POST['image']
		product.save()
		
		
		err_succ['status'] = 1
		err_succ['message'] = 'Изображение добавлено!'
		
	return JsonResponse(err_succ)

#Удаление изображения
def unset_image(request):
	
	product = get_object_or_404(Product, pk=request.POST['product_id'])
	image = get_object_or_404(Image, pk=request.POST['image_id'])
	
	err_succ = {'status': 0, 'message': 'An unknown error occured'}
	
	
	if request.user.is_authenticated == False or product.author != request.user.id:
		return JsonResponse(err_succ)
	

	if request.method == 'POST':
		
		os.remove(settings.BASE_DIR + '/' + str(image.image) )
	
		image.delete()
		
		# Успех!
		err_succ['status'] = 1
		err_succ['message'] = 'Изображение успешно удалено!'
		
	return JsonResponse(err_succ)
	#	Удаление товара
def unset_product(request):
	
	product = get_object_or_404(Product, pk=request.POST['product_id'])
	
	err_succ = {'status': 0, 'message': 'An unknown error occured'}
	
	
	if request.user.is_authenticated == False or product.author != request.user.id:
		return JsonResponse(err_succ)
	
	
	if request.method == 'POST':
		
		for image in product.image_set.all():
			
			os.remove(settings.BASE_DIR + '/' + str(image.image) )
			
			image.delete()
		
	
		product.delete()
		
		# Успех!.
		err_succ['status'] = 1
		err_succ['message'] = 'Продукт успешно удален!'
		
	return JsonResponse(err_succ)
#Регистрация
def user_register(request):
	
	if request.user.is_authenticated:
		return HttpResponseRedirect(Helpers.get_path('user/account'))
	

	form = RegisterForm(request.POST)
	

	err_succ = {'status': 0, 'message': 'Неизвестная ошибка!'}
	
	if request.method == 'POST':
		# check whether it's valid:
		if form.is_valid():
			if User.objects.filter(username=form.cleaned_data['username']).exists():
				err_succ['message'] = 'Username уже существует.'
				
			elif User.objects.filter(email=form.cleaned_data['email']).exists():
				err_succ['message'] = 'Email уже существует.'
				
			elif form.cleaned_data['password'] != form.cleaned_data['password_repeat']:
				err_succ['message'] = 'Пароли не совпадают.'
				
			else:
				# Создание пользователя
				user = User.objects.create_user(
					form.cleaned_data['username'], 
					form.cleaned_data['email'], 
					form.cleaned_data['password']
				)
				user.first_name = form.cleaned_data['first_name']
				user.last_name = form.cleaned_data['last_name']
				
				member = Member.objects.create(
					user = user,
					phone_number = form.cleaned_data['phone_number'],
					about = ''
				)
				
				member.save()
				user.save()
				
				# Вход пользователем
				login(request, user)
				
				# Успешная регистрация
				err_succ['status'] = 1
				err_succ['message'] = 'Вы зарегистрированы'
				
		return JsonResponse(err_succ)


	else:
		return render(request, Helpers.get_url('user/register.html'), {'form': RegisterForm()})
	
def logout(request):
	# Выход из страницы
	django_logout(request)
	return HttpResponseRedirect(Helpers.get_path('user/login'))
