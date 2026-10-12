plugins {
    application
}

val bVersion = (findProperty("bVersion") ?: "1.0").toString()

dependencies {
    implementation("lab.co3:y:1.0")
    implementation("lab.co3:x:1.0")
}

application {
    mainClass.set("lab.co3.Main")
}
