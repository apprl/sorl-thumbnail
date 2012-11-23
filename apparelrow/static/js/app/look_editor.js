jQuery(document).ready(function() {
    window.search_product = new App.Models.SearchProduct();
    window.products = new App.Collections.Products();
    window.facet_container = new App.Models.FacetContainer();
    window.filter_product = new App.Views.FilterProduct({search_product: search_product,
                                                         products: products,
                                                         facet_container: facet_container});
    window.product_list = new App.Views.Products({collection: products});
});
