var gulp = require('gulp');
var gutil = require('gulp-util');
var source = require('vinyl-source-stream');
var watchify = require('watchify');
var browserify = require('browserify');
var envify = require('envify/custom');
var reactify = require('reactify');
var sass = require('gulp-sass');
var task_listing = require('gulp-task-listing');
var notify = require('gulp-notify');

var production = process.env.NODE_ENV === 'production';

var compile_js = function(watch) {
    var bundler = browserify('index', {
        basedir: __dirname,
        debug: !production,
        cache: {},
        packageCache: {},
        fullPaths: watch
    });

    if (watch) {
        bundler = watchify(bundler);
    }

    bundler
        .transform(reactify, {
            harmony: true,
            everything: true,
            target: "es5"
        })
        .transform({
            global: true,
        }, envify({ NODE_ENV: process.env.NODE_ENV || "development", _: 'purge' }));

    var rebundle = function() {
        var pipe = bundler.bundle()
            .on('error', gutil.log.bind(gutil, 'Browserify Error'))
            .pipe(source('index.js'))
            .pipe(gulp.dest('./static/assets'));

        if (process.platform === "darwin") {
            pipe = pipe
                .on('error', notify.onError("Error: <%= error.message %>"))
                .pipe(notify("JS-build finished"));
        }

        return pipe;
    };

    bundler.on('update', rebundle);
    bundler.on('log', gutil.log.bind(gutil));

    return rebundle();
};

gulp.task('scss', function() {
    var bourbon = require('node-bourbon');

    gulp.src('./static/scss/styles.scss')
        .pipe(sass({
            errLogToConsole: true,
            sourceComments: 'map',
            includePaths: bourbon.includePaths
        }))
        .pipe(gulp.dest('./static/assets'));
});

gulp.task('js', function() {
    return compile_js(false);
});

gulp.task('watch', function() {
    // monitor scss for changes
    gulp.start('scss');
    gulp.watch('./static/scss/**/*.scss', ['scss']);

    // return the js bundler in watch mode
    return compile_js(true);
});

gulp.task('help', task_listing);
