#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQuickWindow>
#include <QQuickItem>
#include <QTimer>
#include <QRegion>
#include <QPainterPath>
#include <QDebug>
#include <QQuickImageProvider>
#include <QIcon>
#include <QtGui/qguiapplication_platform.h>
#include <qpa/qplatformwindow_p.h>
#include <wayland-client.h>
#include "background-effect-client.h"
#include <cstring>

struct Effects {
    ext_background_effect_manager_v1 *manager = nullptr;
    bool available = false;
    static void capabilities(void *data, ext_background_effect_manager_v1 *, uint32_t flags) {
        static_cast<Effects*>(data)->available = flags & EXT_BACKGROUND_EFFECT_MANAGER_V1_CAPABILITY_BLUR;
    }
    static void global(void *data, wl_registry *registry, uint32_t name, const char *interface, uint32_t) {
        auto self = static_cast<Effects*>(data);
        if (!std::strcmp(interface, ext_background_effect_manager_v1_interface.name)) {
            self->manager = static_cast<ext_background_effect_manager_v1*>(wl_registry_bind(registry,name,&ext_background_effect_manager_v1_interface,1));
            static const ext_background_effect_manager_v1_listener listener = {capabilities};
            ext_background_effect_manager_v1_add_listener(self->manager,&listener,self);
        }
    }
    static void removed(void *, wl_registry *, uint32_t) {}
};

class AppIconProvider : public QQuickImageProvider {
public:
    AppIconProvider() : QQuickImageProvider(QQuickImageProvider::Pixmap) {}
    QPixmap requestPixmap(const QString &id, QSize *size, const QSize &requested) override {
        QIcon icon = id.startsWith('/') ? QIcon(id) : QIcon::fromTheme(id);
        if(icon.isNull()) icon=QIcon::fromTheme("application-x-executable");
        if(icon.isNull()) icon=QIcon::fromTheme("applications-other");
        QSize target=requested.isValid() ? requested : QSize(32,32);
        QPixmap pixmap=icon.pixmap(target);
        if(pixmap.isNull()) { pixmap=QPixmap(target);pixmap.fill(QColor("#8c98ac")); }
        if(size) *size=pixmap.size();
        return pixmap;
    }
};

int main(int argc, char **argv) {
    QGuiApplication app(argc,argv);
    app.setApplicationName("unixporn-board");
    app.setDesktopFileName("unixporn-board");
    QQmlApplicationEngine engine;
    engine.addImageProvider("appicons",new AppIconProvider);
    engine.load(QUrl::fromLocalFile(app.applicationDirPath()+"/../Desktop.qml"));
    if (engine.rootObjects().isEmpty()) return 1;
    auto window=qobject_cast<QQuickWindow*>(engine.rootObjects().first());
    auto nativeApp=app.nativeInterface<QNativeInterface::QWaylandApplication>();
    if (!window || !nativeApp) return app.exec();
    Effects effects;
    auto registry=wl_display_get_registry(nativeApp->display());
    static const wl_registry_listener listener={Effects::global,Effects::removed};
    wl_registry_add_listener(registry,&listener,&effects);
    wl_display_roundtrip(nativeApp->display());
    wl_display_roundtrip(nativeApp->display());
    ext_background_effect_surface_v1 *surfaceEffect=nullptr;
    QRegion lastRegion;
    QTimer timer;
    QObject::connect(&timer,&QTimer::timeout,[&] {
        if (!effects.available || !window->isExposed()) return;
        auto nativeWindow=window->nativeInterface<QNativeInterface::Private::QWaylandWindow>();
        if (!nativeWindow || !nativeWindow->surface()) return;
        if (!surfaceEffect) {
            surfaceEffect=ext_background_effect_manager_v1_get_background_effect(effects.manager,nativeWindow->surface());
            qInfo()<<"Panel blur: Wayland region enabled";
        }
        QRegion region;
        for (auto item:window->findChildren<QQuickItem*>("dashboardPanel")) {
            if (!item->isVisible() || item->width()<=0 || item->height()<=0) continue;
            auto pos=item->mapToScene(QPointF(0,0));
            QPainterPath path;
            qreal radius=item->property("radius").toReal();
            path.addRoundedRect(QRectF(pos,QSizeF(item->width(),item->height())),radius,radius);
            region+=QRegion(path.toFillPolygon().toPolygon());
        }
        if (region==lastRegion) return;
        lastRegion=region;
        auto nativeRegion=wl_compositor_create_region(nativeApp->compositor());
        for (auto rect:region) wl_region_add(nativeRegion,rect.x(),rect.y(),rect.width(),rect.height());
        ext_background_effect_surface_v1_set_blur_region(surfaceEffect,nativeRegion);
        wl_region_destroy(nativeRegion);
        window->update();
        wl_display_flush(nativeApp->display());
    });
    timer.start(150);
    int result=app.exec();
    timer.stop();
    if (surfaceEffect) ext_background_effect_surface_v1_destroy(surfaceEffect);
    if (effects.manager) ext_background_effect_manager_v1_destroy(effects.manager);
    wl_registry_destroy(registry);
    return result;
}
