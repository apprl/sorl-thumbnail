# Require any additional compass plugins here.
# Set this to the root of your project when deployed:
http_path = "/media"
css_dir = "styles"
sass_dir = "src"
images_dir = "images"
fonts_dir = "fonts"
javascripts_dir = "js"
# To enable relative paths to assets via compass helper functions. Uncomment:
# relative_assets = true

static_host = 'http://localhost:8000'

asset_host do |asset|
  static_host
end
