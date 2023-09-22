from flask import Flask, render_template, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, UserMixin, logout_user, login_required, current_user
from datetime import datetime
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///groceryapp.sqlite3"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key="secret@1234"

db=SQLAlchemy(app)

login_manager=LoginManager()
login_manager.init_app(app)


#User Class
class User(UserMixin,db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=False)
    mobile = db.Column(db.String, unique=True, nullable=False)
    fName = db.Column(db.String, nullable=False)
    lName = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)
    cnfPassword = db.Column(db.String, nullable=False)

    def __repr__(self) -> str:
        return '<User %r>' % self.fName
    
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(100), unique=True)
    # product = db.relationship('Product', cascade='all, delete')
    products = db.relationship('Product', back_populates='category')

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100))
    quantity=db.Column(db.Integer)
    mfg_date = db.Column(db.Date)
    exp_date = db.Column(db.Date)
    rate_per_unit = db.Column(db.Float)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    # category = db.relationship('Category', backref=db.backref('products', lazy='dynamic'))
    category = db.relationship('Category', back_populates='products')

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('cart', lazy='dynamic'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship('Product', backref=db.backref('carts', lazy='dynamic'))
    quantity = db.Column(db.Integer)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    rate_per_unit = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('orders', lazy='dynamic'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer)
    order_date = db.Column(db.DateTime)
    user = db.relationship('User', backref=db.backref('orders', lazy='dynamic'))
    product = db.relationship('Product', backref=db.backref('orders', lazy='dynamic'))
    

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

##########################################
#            USER SIDE                   #
##########################################

# Home page. What user sees

@app.route('/')
def index():
    categories=Category.query.all()
    user_id=User.query.all()
    products = db.session.query(Product, Product.quantity).group_by(Product.product_name).all()
    return render_template("index.html",categories=categories, products=products, user_id=user_id)


#   LOGIN

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        email=request.form.get('email')
        password=request.form.get('password')
        user=User.query.filter_by(email=email).scalar()
        #Admin login
        if email=="dp@gmail.com" and password=="1234":
            login_user(user)
            return redirect("/categories")
    
        
        elif user and password==user.password:
            login_user(user)
            return redirect('/')

        else:
            flash('Please check your email and password or SignUp!','warning')
            return redirect('/login')

    return render_template('login.html')


#    LOGOUT

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

#   SIGNUP

@app.route('/signup',methods=["GET","POST"])
def signup():
    if request.method=="POST":
        email=request.form.get('email')
        mobile=request.form.get('mobile')
        fName=request.form.get('fName')
        lName=request.form.get('lName')
        password=request.form.get('password')
        cnfPassword=request.form.get('cnfPassword')
        user=User(email=email,mobile=mobile,fName=fName,lName=lName,password=password,cnfPassword=cnfPassword)
        db.session.add(user)
        db.session.commit()
        flash('Sign-Up Succesful!','success')
        return redirect('/login')

    return render_template("signup.html")


# USER PROFILE

@app.route('/user_profile')
@login_required
def user_profile():
    user_id = current_user.get_id()
    user = User.query.get(user_id)
    orders = Order.query.filter_by(user_id=user_id).all()
    return render_template('user_profile.html', user=user, orders=orders)


# CATEGORIES PAGE FOR USER

@app.route('/category/<int:category_id>')
def category_page(category_id):
    category = Category.query.get(category_id)
    products = db.session.query(Product, Product.quantity).filter_by(category_id=category_id).group_by(Product.product_name).all()
    return render_template("category_page.html", category=category, products=products)



#ADDING TO CART
# Foreach Purchase there should be a different cart
# Cart => DNE => create a new cart
# Cart => If exists => Product match => Increase Quantity
#                   => create new product


@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    user_id = current_user.get_id()
    product_id = request.form['product_id']
    quantity = int(request.form['quantity'])

    cart = Cart.query.filter_by(user_id=user_id).first()

    if not cart:
        cart = Cart(user_id=user_id)
        db.session.add(cart)
        db.session.commit()

    cart_item = CartItem.query.filter_by(cart_id=cart.id, user_id=user_id, product_id=product_id).first()

    product = Product.query.get(product_id)
    rate_per_unit = product.rate_per_unit

    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(
            product_id=product_id,
            quantity=quantity,
            rate_per_unit=rate_per_unit,
            user_id=user_id,
            cart_id=cart.id
        )
        db.session.add(cart_item)
    db.session.commit()
    flash('Product added to cart successfully!', 'success')

    return redirect(url_for('index'))

#DISPLAYING CART

# If cart is empty show "cart is empty message else show cart.html"

@app.route('/cart')
@login_required
def cart():
    user_id = current_user.get_id()
    cart = Cart.query.filter_by(user_id=user_id).first()
    if cart is None:
        cart_items=[]
        cart_items_count=0
        total_cost=0
    else:
        cart_items = CartItem.query.filter_by(cart_id=cart.id).all()
        cart_items_count = len(cart_items)

        total_cost = sum(item.quantity * item.rate_per_unit for item in cart_items)

    for cart_item in cart_items:
        product = Product.query.get(cart_item.product_id)
        cart_item.product_name = product.product_name

    return render_template('cart.html', cart_items=cart_items, cart_items_count=cart_items_count, total_cost=total_cost)


#DELETING ITEMS FROM CART

@app.route('/delete_cart_item/<int:item_id>', methods=['POST'])
@login_required
def delete_cart_item(item_id):
    cart_item = CartItem.query.get(item_id)
    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()
        flash('Item deleted successfully!', 'danger')

    return redirect(url_for('cart'))



#  CHECKOUT

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    user_id = current_user.get_id()
    cart = Cart.query.filter_by(user_id=user_id).first()
    cart_items = CartItem.query.filter_by(cart_id=cart.id).all()

    # Moving items from cart to order history after checkout button is clicked
    for item in cart_items:
        product=Product.query.get(item.product_id)
        quantity_left= product.quantity - item.quantity
        if quantity_left >= 0:
            order = Order(
                user_id=user_id,
                product_id=item.product_id,
                quantity=item.quantity,
                order_date=datetime.now()
            )
            db.session.add(order)
            product.quantity=quantity_left

        else:
            item.quantity = product.quantity
            product.quantity = 0

    db.session.commit()

    for item in cart_items:
        db.session.delete(item)

    db.session.commit()

    flash('Order Successful! Please visit again.','success')
    return redirect(url_for('index'))



# SEARCHING

@app.route('/search_results')
def search_results():
    search_query = request.args.get('search_keywords')

    products = Product.query.filter(Product.product_name.ilike(f'%{search_query}%')).all()
    
    return render_template('search_results.html', products=products)





##############################
#    ADMIN SIDE OPERATIONS   #
##############################

#-----------------------------#
#     CRUD ON PRODUCTS        # 
#-----------------------------#

#ADDING PRODUCTS

@app.route('/category/<int:category_id>/add_products', methods=["GET", "POST"])
def add_product(category_id):
    category = Category.query.get(category_id)
    if request.method == 'POST':
        product_name = request.form.get("product_name")
        quantity = request.form.get('quantity')
        mfg_date = datetime.strptime(request.form.get("mfg_date"), '%Y-%m-%d').date()
        exp_date = datetime.strptime(request.form.get("exp_date"), '%Y-%m-%d').date()
        rate_per_unit = request.form.get("rate_per_unit")

        product = Product(product_name=product_name, quantity=quantity, mfg_date=mfg_date, rate_per_unit=rate_per_unit, exp_date=exp_date, category=category)

        db.session.add(product)
        db.session.commit()

        flash('Product added successfully!', 'success')
        return redirect(url_for('add_product', category_id=category_id))
    
    return render_template("add_product.html",category=category, category_id=category_id)



#   EDITING PRODUCTS

@app.route('/edit_product/<int:category_id>/<int:product_id>', methods=["GET", "POST"])
def edit_product(category_id, product_id):
    category = Category.query.get(category_id)
    product = Product.query.get(product_id)
    
    if request.method == 'POST':
        product.product_name = request.form.get('product_name')
        product.quantity = request.form.get('quantity')
        product.rate_per_unit = request.form.get('rate_per_unit')
        product.mfg_date = datetime.strptime(request.form.get('mfg_date'), '%Y-%m-%d').date()
        product.exp_date = datetime.strptime(request.form.get('exp_date'), '%Y-%m-%d').date()
        
        db.session.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('add_product', category_id=category_id))
    
    return render_template('edit_product.html', category=category, product=product, category_id=category_id)

#   DELETING PRODUCTS 

@app.route('/delete_product/<int:category_id>/<int:product_id>', methods=["POST"])
def delete_product(category_id, product_id):
    product = Product.query.get(product_id)

    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully!', 'danger')
    return redirect(url_for('add_product', category_id=category_id))


#-----------------------------#
#     CRUD ON CATEGORIES      # 
#-----------------------------#


#CREATING CATEGORIES

@app.route('/add_categories', methods=["GET","POST"])
@login_required
def add_categories():
    if request.method == "POST":
        category_name = request.form.get('category_name')

        # checking if the category already exists
        added_category = Category.query.filter_by(category_name=category_name).first()
        if added_category:
            flash('Category already exists!', 'warning')
        else:
            category = Category(category_name=category_name)

            try:
                db.session.add(category)
                db.session.commit()
                flash('Category added successfully!', 'success')
            except IntegrityError:
                db.session.rollback()
                flash('Error: Category could not be added!', 'danger')

        return redirect(url_for('categories'))

    return render_template("add_categories.html")

#DISPLAYING CATEGORIES  TO ADMIN

@app.route('/categories', methods=['GET', 'POST'])
@login_required
def categories():
    categories = Category.query.all()
    return render_template('categories.html', categories=categories)

# EDITING CATEGORY

@app.route('/edit_category/<int:category_id>', methods = ['GET', 'POST'])
@login_required
def edit_category(category_id):
    category = Category.query.get(category_id)

    if request.method == 'POST':
        category.category_name = request.form.get('category_name')

        db.session.commit()
        flash('Category name updated successfully', 'success')
        return redirect(url_for('categories'))
    
    return render_template('edit_category.html', category=category)

#Deleting Categories
@app.route('/delete_category/<int:category_id>', methods=['POST'])
@login_required
def delete_category(category_id):
    category = Category.query.get(category_id)
    db.session.delete(category)
    db.session.commit()
    flash('Category deleted successfully!', 'danger')
    return redirect('/categories')


if __name__== "__main__":
    app.run(debug=True, port=8000)